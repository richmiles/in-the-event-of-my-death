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
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json


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
        if run_full_smoke_test(base_url):
            return 0
        return 1
    except Exception as e:
        log(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
