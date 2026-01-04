#!/usr/bin/env python3
"""
Smoke test for IEOMD staging/production deployments.

Tests the full secret creation flow:
1. Health check
2. Request PoW challenge
3. Solve PoW
4. Create secret
5. Check secret status via edit token
6. Check secret status via decrypt token
7. Check secret status via public id

Usage:
    ./scripts/smoke-test.py https://staging.example.com
    ./scripts/smoke-test.py https://staging.example.com --health-only
"""

import argparse
import base64
import hashlib
import json
import re
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"API error {status_code}: {body}")
        self.status_code = status_code
        self.body = body


SHORT_UNLOCK_SECONDS = 20
EXPIRY_GAP_MINUTES = 65
MIN_UNLOCK_BUFFER_SECONDS = 5
UNLOCK_SOON_MAX_SECONDS = 90
UNLOCK_POLL_DEADLINE_SECONDS = 120
UNLOCK_POLL_SLEEP_SECONDS = 2


def log(msg: str) -> None:
    """Print timestamped log message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def api_request(
    base_url: str,
    method: str,
    path: str,
    data: dict | None = None,
    headers: dict[str, str] | None = None,
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
        raise ApiError(e.code, error_body) from e


def parse_utc_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def compute_unlock_at_for_environment(desired_unlock_at: datetime, api_error: ApiError) -> datetime | None:
    """
    If the API rejected unlock_at due to environment min unlock policy, return an adjusted unlock_at.
    """
    if api_error.status_code not in (400, 422):
        return None

    m = re.search(r"Unlock date must be at least (\\d+) minutes in the future", api_error.body)
    if not m:
        return None

    min_minutes = int(m.group(1))
    now = datetime.now(timezone.utc)
    adjusted = now + timedelta(minutes=min_minutes, seconds=5)
    if adjusted > desired_unlock_at:
        return adjusted
    return None


def http_get(
    url: str,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    req = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.getcode(), dict(response.headers.items()), response.read()
    except HTTPError as e:
        error_body = e.read() if e.fp else b""
        resp_headers = dict(e.headers.items()) if e.headers else {}
        return e.code, resp_headers, error_body


class _HTMLAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.asset_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: v for k, v in attrs if v is not None}

        if tag == "script":
            src = attrs_dict.get("src")
            if src:
                self.asset_urls.append(src)

        if tag == "link":
            rel = (attrs_dict.get("rel") or "").lower()
            href = attrs_dict.get("href")
            if not href:
                return
            # Vite commonly uses <link rel="modulepreload" href="..."> for JS chunks.
            if any(token in rel for token in ("stylesheet", "modulepreload", "preload")):
                self.asset_urls.append(href)


def check_web_serving(base_url: str) -> None:
    """
    Verify the web frontend is being served.

    - GET / returns 200 and looks like HTML
    - At least one referenced same-origin asset (script/css) loads (200)
    """
    homepage_url = f"{base_url}/"
    log(f"Checking web homepage: {homepage_url}")
    status, resp_headers, body = http_get(homepage_url, timeout=20.0)
    content_type_header = next(
        (v for k, v in resp_headers.items() if k.lower() == "content-type"),
        "",
    )
    if status != 200:
        raise RuntimeError(
            f"Homepage returned non-200: {status} "
            f"(content_type={content_type_header!r}, body_preview={body[:200]!r})"
        )

    content_type = content_type_header.lower()
    if "text/html" not in content_type:
        raise RuntimeError(f"Homepage Content-Type not HTML: {content_type!r}")

    if not body:
        raise RuntimeError("Homepage returned empty body")

    body_text = body.decode("utf-8", errors="replace")
    if 'id="root"' not in body_text and "id='root'" not in body_text:
        if len(body) < 200:
            raise RuntimeError(
                "Homepage HTML missing expected root marker and is unexpectedly small "
                f"({len(body)} bytes, preview={body[:200]!r})"
            )
        log("WARNING: Homepage HTML missing expected root marker (id=\"root\"); continuing")

    parser = _HTMLAssetParser()
    parser.feed(body_text)

    base_parsed = urlparse(base_url)
    base_netloc = base_parsed.netloc
    if not base_netloc:
        raise RuntimeError(f"Unable to parse netloc from base_url: {base_url!r}")

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
        # "Same-origin" for smoke test purposes: same scheme/host/port.
        if parsed.netloc != base_netloc:
            continue
        resolved_assets.append(absolute)

    unique_assets = list(dict.fromkeys(resolved_assets))
    log(
        "Assets discovered: "
        f"raw={len(parser.asset_urls)} candidates={len(resolved_assets)} unique={len(unique_assets)}"
    )
    if not unique_assets:
        raw_assets = list(dict.fromkeys(parser.asset_urls))[:10]
        raise RuntimeError(
            "No loadable same-origin JS/CSS assets found in homepage HTML "
            f"(base_netloc={base_netloc!r}, found={raw_assets!r})"
        )

    # Fetch at most 1 asset to keep runtime low while still catching broken static hosting.
    for asset_url in unique_assets[:1]:
        log(f"Fetching asset: {asset_url}")
        asset_status, _, asset_body = http_get(
            asset_url,
            timeout=20.0,
            headers={"Accept": "*/*"},
        )
        if asset_status != 200:
            raise RuntimeError(
                f"Asset returned non-200: {asset_status} ({asset_url}, preview={asset_body[:200]!r})"
            )
        if not asset_body:
            raise RuntimeError(f"Asset returned empty body: {asset_url}")

    log("Web checks passed (assets fetched: 1)")


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
    # Keep unlock short when allowed (faster smoke), but adapt if env enforces a minimum.
    now = datetime.now(timezone.utc)
    unlock_at = now + timedelta(seconds=20)
    expires_at = unlock_at + timedelta(minutes=65)

    log("Creating secret")
    create_payload = {
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
    }

    try:
        secret = api_request(base_url, "POST", "/secrets", data=create_payload)
    except ApiError as e:
        adjusted_unlock_at = compute_unlock_at_for_environment(unlock_at, e)
        if not adjusted_unlock_at:
            raise
        unlock_at = adjusted_unlock_at
        expires_at = unlock_at + timedelta(minutes=65)
        create_payload["unlock_at"] = unlock_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        create_payload["expires_at"] = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        log(f"Create rejected; retrying with unlock_at={create_payload['unlock_at']}")
        secret = api_request(base_url, "POST", "/secrets", data=create_payload)

    secret_id = secret["secret_id"]
    log(f"Secret created: id={secret_id}, unlock_at={secret['unlock_at']}")

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

    if status.get("status") not in ("pending", "available"):
        log(f"ERROR: Unexpected edit status '{status.get('status')}'")
        return False

    log(f"Status verified: exists={status['exists']}, status={status['status']}")

    # Step 6: Check status via decrypt token (should not consume the secret)
    log("Checking secret status via decrypt token")
    decrypt_status = api_request(
        base_url,
        "GET",
        "/secrets/status",
        headers={"Authorization": f"Bearer {decrypt_token}"},
    )

    if not decrypt_status.get("exists"):
        log("ERROR: Secret not found via decrypt token")
        return False

    if decrypt_status.get("status") not in ("pending", "available"):
        log(f"ERROR: Unexpected decrypt status '{decrypt_status.get('status')}'")
        return False

    # Step 7: Check public status via secret ID and assert consistent status mapping
    log("Checking secret status via public ID endpoint")
    public_status = api_request(base_url, "GET", f"/secrets/{secret_id}/status")

    if public_status.get("id") != secret_id:
        log("ERROR: Public status endpoint returned mismatched secret id")
        return False

    expected_public_status = (
        "unlocked" if decrypt_status.get("status") == "available" else decrypt_status.get("status")
    )
    if public_status.get("status") != expected_public_status:
        log(
            f"ERROR: Expected public status '{expected_public_status}', got '{public_status.get('status')}'"
        )
        return False

    # Optional: if unlock happens soon, wait briefly and verify available->unlocked mapping.
    # (Keep bounded to avoid long smoke runtimes.)
    try:
        unlock_at_api = parse_utc_datetime(secret["unlock_at"])
        seconds_until_unlock = (unlock_at_api - datetime.now(timezone.utc)).total_seconds()
    except Exception:
        seconds_until_unlock = 9999

    if 0 < seconds_until_unlock <= 90:
        log("Waiting briefly for unlock to verify status mapping")
        deadline = time.time() + 120
        while time.time() < deadline:
            current = api_request(
                base_url,
                "GET",
                "/secrets/status",
                headers={"Authorization": f"Bearer {decrypt_token}"},
            )
            if current.get("exists") and current.get("status") == "available":
                public_current = api_request(base_url, "GET", f"/secrets/{secret_id}/status")
                if public_current.get("status") != "unlocked":
                    log(
                        f"ERROR: Expected public status 'unlocked' after available, got '{public_current.get('status')}'"
                    )
                    return False
                break
            time.sleep(2)

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
