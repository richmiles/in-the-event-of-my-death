#!/usr/bin/env python3
"""
Smoke test for IEOMD staging/production deployments.

Tests the full secret creation flow:
1. Health check
2. Request PoW challenge
3. Solve PoW
4. Create secret
5. Check secret status via edit token

Usage:
    ./scripts/smoke-test.py https://staging.example.com
    ./scripts/smoke-test.py https://staging.example.com --health-only
"""

import argparse
import base64
import hashlib
import json
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


def log(msg: str) -> None:
    """Print timestamped log message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def api_request(
    base_url: str,
    method: str,
    path: str,
    data: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """Make an API request and return JSON response."""
    url = f"{base_url}/api/v1{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode() if data else None
    request = Request(url, data=body, headers=req_headers, method=method)

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"API error {e.code}: {error_body}") from e


def http_get(url: str, timeout: float = 30.0, headers: dict | None = None) -> tuple[int, dict, bytes]:
    req = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.getcode(), dict(response.headers.items()), response.read()
    except HTTPError as e:
        error_body = e.read() if e.fp else b""
        raise RuntimeError(f"HTTP error {e.code} for {url}: {error_body[:500]!r}") from e


class _HTMLAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.asset_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)

        if tag == "script":
            src = attrs_dict.get("src")
            if src:
                self.asset_urls.append(src)

        if tag == "link":
            rel = (attrs_dict.get("rel") or "").lower()
            href = attrs_dict.get("href")
            if href and "stylesheet" in rel:
                self.asset_urls.append(href)


def check_web_serving(base_url: str) -> bool:
    """
    Verify the web frontend is being served.

    - GET / returns 200 and looks like HTML
    - At least one referenced same-origin asset (script/css) loads (200)
    """
    homepage_url = f"{base_url}/"
    log(f"Checking web homepage: {homepage_url}")
    status, resp_headers, body = http_get(homepage_url, timeout=20.0)
    if status != 200:
        raise RuntimeError(f"Homepage returned non-200: {status}")

    content_type = (resp_headers.get("Content-Type") or "").lower()
    if "text/html" not in content_type:
        raise RuntimeError(f"Homepage Content-Type not HTML: {content_type!r}")

    if not body or len(body) < 200:
        raise RuntimeError(f"Homepage response too small ({len(body)} bytes)")

    body_text = body.decode("utf-8", errors="replace")
    parser = _HTMLAssetParser()
    parser.feed(body_text)

    base_netloc = urlparse(base_url).netloc
    base_labels = [label for label in base_netloc.split(".") if label]
    base_root_domain = ".".join(base_labels[-2:]) if len(base_labels) >= 2 else base_netloc

    def is_allowed_asset_host(host: str) -> bool:
        return host == base_netloc or host == base_root_domain or host.endswith(f".{base_root_domain}")

    def looks_like_static_asset(path: str) -> bool:
        lower = path.lower()
        return (
            "/assets/" in lower
            or lower.endswith(".js")
            or lower.endswith(".mjs")
            or lower.endswith(".css")
        )

    resolved_assets: list[str] = []
    for asset_url in parser.asset_urls:
        absolute = urljoin(homepage_url, asset_url)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not looks_like_static_asset(parsed.path):
            continue
        if not is_allowed_asset_host(parsed.netloc):
            continue
        resolved_assets.append(absolute)

    unique_assets = list(dict.fromkeys(resolved_assets))
    if not unique_assets:
        raw_assets = list(dict.fromkeys(parser.asset_urls))[:10]
        raise RuntimeError(
            "No loadable JS/CSS assets found in homepage HTML "
            f"(base_host={base_netloc!r}, base_root={base_root_domain!r}, found={raw_assets!r})"
        )

    # Fetch at most 2 assets to keep runtime low while still catching broken static hosting.
    for asset_url in unique_assets[:2]:
        log(f"Fetching asset: {asset_url}")
        asset_status, _, asset_body = http_get(
            asset_url,
            timeout=20.0,
            headers={"Accept": "*/*"},
        )
        if asset_status != 200:
            raise RuntimeError(f"Asset returned non-200: {asset_status} ({asset_url})")
        if not asset_body:
            raise RuntimeError(f"Asset returned empty body: {asset_url}")

    log(f"Web checks passed (assets fetched: {min(len(unique_assets), 2)}/{len(unique_assets)})")
    return True


def wait_for_health(base_url: str, max_attempts: int = 30, delay: float = 2.0) -> bool:
    """Wait for /health to return healthy status."""
    url = f"{base_url}/health"

    for attempt in range(1, max_attempts + 1):
        try:
            request = Request(url)
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data.get("status") == "healthy":
                    log(f"Health check passed (attempt {attempt})")
                    return True
        except (HTTPError, URLError, json.JSONDecodeError, TimeoutError):
            pass

        if attempt < max_attempts:
            time.sleep(delay)

    return False


def solve_pow(nonce: str, payload_hash: str, difficulty: int) -> int:
    """
    Solve proof-of-work challenge.

    Finds counter where SHA256(nonce || counter_hex || payload_hash) has
    'difficulty' leading zero bits.
    """
    target = 2 ** (256 - difficulty)

    counter = 0
    start_time = time.time()

    while True:
        preimage = f"{nonce}{counter:016x}{payload_hash}"
        hash_bytes = hashlib.sha256(preimage.encode()).digest()
        hash_int = int.from_bytes(hash_bytes, "big")

        if hash_int < target:
            elapsed = time.time() - start_time
            log(f"PoW solved: counter={counter} ({elapsed:.2f}s, {counter/elapsed:.0f} H/s)")
            return counter

        counter += 1

        # Progress update every million attempts
        if counter % 1_000_000 == 0:
            elapsed = time.time() - start_time
            log(f"PoW progress: {counter:,} attempts ({counter/elapsed:.0f} H/s)")


def generate_test_secret() -> tuple[str, str, str, str]:
    """
    Generate fake encrypted data for testing.

    Returns (ciphertext_b64, iv_b64, auth_tag_b64, payload_hash)
    """
    # Small ciphertext for minimal PoW difficulty
    ciphertext = b"smoke-test-" + secrets.token_bytes(21)  # 32 bytes total
    iv = secrets.token_bytes(12)
    auth_tag = secrets.token_bytes(16)

    ciphertext_b64 = base64.b64encode(ciphertext).decode()
    iv_b64 = base64.b64encode(iv).decode()
    auth_tag_b64 = base64.b64encode(auth_tag).decode()

    # Compute payload hash (same as backend)
    payload_hash = hashlib.sha256(ciphertext + iv + auth_tag).hexdigest()

    return ciphertext_b64, iv_b64, auth_tag_b64, payload_hash


def run_full_smoke_test(base_url: str) -> bool:
    """Run the complete smoke test flow."""
    log("Starting full smoke test")

    # Step 1: Generate test data
    log("Generating test secret data")
    ciphertext_b64, iv_b64, auth_tag_b64, payload_hash = generate_test_secret()
    ciphertext_size = len(base64.b64decode(ciphertext_b64))
    edit_token = secrets.token_hex(32)
    decrypt_token = secrets.token_hex(32)

    # Step 2: Request PoW challenge
    log("Requesting PoW challenge")
    challenge = api_request(
        base_url,
        "POST",
        "/challenges",
        data={"payload_hash": payload_hash, "ciphertext_size": ciphertext_size},
    )
    log(f"Got challenge: difficulty={challenge['difficulty']}, expires={challenge['expires_at']}")

    # Step 3: Solve PoW
    log(f"Solving PoW (difficulty={challenge['difficulty']})")
    counter = solve_pow(challenge["nonce"], payload_hash, challenge["difficulty"])

    # Step 4: Create secret
    # Use minimum allowed times (5 min unlock, 60 min gap, so 65 min expiry)
    now = datetime.now(timezone.utc)
    unlock_at = now + timedelta(minutes=6)  # Slightly over minimum
    expires_at = unlock_at + timedelta(minutes=65)  # Slightly over minimum gap

    log("Creating secret")
    secret = api_request(
        base_url,
        "POST",
        "/secrets",
        data={
            "ciphertext": ciphertext_b64,
            "iv": iv_b64,
            "auth_tag": auth_tag_b64,
            "unlock_at": unlock_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "edit_token": edit_token,
            "decrypt_token": decrypt_token,
            "pow_proof": {
                "challenge_id": challenge["challenge_id"],
                "nonce": challenge["nonce"],
                "counter": counter,
                "payload_hash": payload_hash,
            },
        },
    )
    log(f"Secret created: id={secret['secret_id']}, unlock_at={secret['unlock_at']}")

    # Step 5: Check status via edit token
    log("Checking secret status via edit token")
    status = api_request(
        base_url,
        "GET",
        "/secrets/edit/status",
        headers={"Authorization": f"Bearer {edit_token}"},
    )

    if not status.get("exists"):
        log("ERROR: Secret not found via edit token")
        return False

    if status.get("status") != "pending":
        log(f"ERROR: Expected status 'pending', got '{status.get('status')}'")
        return False

    log(f"Status verified: exists={status['exists']}, status={status['status']}")
    log("Full smoke test PASSED")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="IEOMD smoke test")
    parser.add_argument("base_url", help="Base URL (e.g., https://staging.example.com)")
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="Only run health check, skip full flow",
    )
    parser.add_argument(
        "--skip-web",
        action="store_true",
        help="Skip web homepage/assets checks (not recommended for staging/prod)",
    )
    parser.add_argument(
        "--max-health-attempts",
        type=int,
        default=30,
        help="Max health check attempts (default: 30)",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    # Always start with health check
    log(f"Checking health: {base_url}/health")
    if not wait_for_health(base_url, max_attempts=args.max_health_attempts):
        log("ERROR: Health check failed")
        return 1

    if args.health_only:
        log("Health-only mode: skipping full flow")
        return 0

    # Run full smoke test
    try:
        if not args.skip_web:
            check_web_serving(base_url)
        if run_full_smoke_test(base_url):
            return 0
        return 1
    except Exception as e:
        log(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
