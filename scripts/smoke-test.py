#!/usr/bin/env python3
"""
Smoke test for IEOMD staging/production deployments.

Tests the full secret creation flow:
1. Health check
2. Request PoW challenge
3. Solve PoW
4. Create secret
5. Check secret status via edit token
6. Edit secret dates via edit token and re-check status

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


def parse_utc_datetime(value: str) -> datetime:
    """
    Parse an API UTC datetime string.

    Backend responses are expected to be ISO-like with a trailing "Z"
    (e.g., "2025-01-01T12:34:56Z").
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"Invalid datetime value: {value!r}")

    if value.endswith("Z"):
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_utc_datetime(dt: datetime) -> str:
    dt_utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return dt_utc.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        raise RuntimeError(f"API error {e.code}: {error_body}") from e


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
    # Keep unlock safely in the future to avoid flakiness during slow runs.
    now = datetime.now(timezone.utc)
    unlock_at = now + timedelta(minutes=10)
    expires_at = unlock_at + timedelta(minutes=65)

    log("Creating secret")
    secret = api_request(
        base_url,
        "POST",
        "/secrets",
        data={
            "ciphertext": ciphertext_b64,
            "iv": iv_b64,
            "auth_tag": auth_tag_b64,
            "unlock_at": format_utc_datetime(unlock_at),
            "expires_at": format_utc_datetime(expires_at),
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
    created_unlock_at = parse_utc_datetime(secret["unlock_at"])
    created_expires_at = parse_utc_datetime(secret["expires_at"])
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

    status_unlock_at = parse_utc_datetime(status["unlock_at"])
    status_expires_at = parse_utc_datetime(status["expires_at"])
    if status_unlock_at != created_unlock_at or status_expires_at != created_expires_at:
        log(
            "ERROR: Status timestamps do not match create response: "
            f"create=({created_unlock_at.isoformat()}, {created_expires_at.isoformat()}) "
            f"status=({status_unlock_at.isoformat()}, {status_expires_at.isoformat()})"
        )
        return False

    log(f"Status verified: exists={status['exists']}, status={status['status']}")

    # Step 6: Edit secret dates and re-check status remains pending
    log("Editing secret dates via edit token")
    new_unlock_at = (created_unlock_at + timedelta(minutes=5)).replace(microsecond=0)
    new_expires_at = (created_expires_at + timedelta(minutes=5)).replace(microsecond=0)

    if new_unlock_at >= new_expires_at:
        log("ERROR: Computed invalid edited timestamps (unlock >= expiry)")
        return False

    if (new_expires_at - new_unlock_at) < timedelta(minutes=15):
        log("ERROR: Computed invalid edited timestamps (gap < 15 minutes)")
        return False

    edited = api_request(
        base_url,
        "PUT",
        "/secrets/edit",
        headers={"Authorization": f"Bearer {edit_token}"},
        data={
            "unlock_at": format_utc_datetime(new_unlock_at),
            "expires_at": format_utc_datetime(new_expires_at),
        },
    )

    edited_unlock_at = parse_utc_datetime(edited["unlock_at"])
    edited_expires_at = parse_utc_datetime(edited["expires_at"])
    if edited_unlock_at != new_unlock_at or edited_expires_at != new_expires_at:
        log(
            "ERROR: Edit response timestamps do not match request: "
            f"requested=({new_unlock_at.isoformat()}, {new_expires_at.isoformat()}) "
            f"edited=({edited_unlock_at.isoformat()}, {edited_expires_at.isoformat()})"
        )
        return False

    if edited_unlock_at <= created_unlock_at or edited_expires_at <= created_expires_at:
        log("ERROR: Edit did not postpone timestamps as expected")
        return False

    log("Re-checking secret edit status after edit")
    status2 = api_request(
        base_url,
        "GET",
        "/secrets/edit/status",
        headers={"Authorization": f"Bearer {edit_token}"},
    )

    if not status2.get("exists"):
        log("ERROR: Secret not found via edit token after edit")
        return False

    if status2.get("status") != "pending":
        log(f"ERROR: Expected status 'pending' after edit, got '{status2.get('status')}'")
        return False

    status2_unlock_at = parse_utc_datetime(status2["unlock_at"])
    status2_expires_at = parse_utc_datetime(status2["expires_at"])
    if status2_unlock_at != edited_unlock_at or status2_expires_at != edited_expires_at:
        log(
            "ERROR: Status timestamps do not reflect edit: "
            f"expected=({edited_unlock_at.isoformat()}, {edited_expires_at.isoformat()}) "
            f"status=({status2_unlock_at.isoformat()}, {status2_expires_at.isoformat()})"
        )
        return False

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
