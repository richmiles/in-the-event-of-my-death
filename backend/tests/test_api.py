"""Comprehensive tests for the secrets API."""

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta


def utcnow():
    """Get current UTC time as naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


def generate_test_data():
    """Generate test cryptographic data."""
    # Simulating what the frontend would generate
    iv = secrets.token_bytes(12)
    auth_tag = secrets.token_bytes(16)
    ciphertext = secrets.token_bytes(100)  # Fake ciphertext
    edit_token = secrets.token_hex(32)
    decrypt_token = secrets.token_hex(32)

    return {
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "iv": base64.b64encode(iv).decode(),
        "auth_tag": base64.b64encode(auth_tag).decode(),
        "edit_token": edit_token,
        "decrypt_token": decrypt_token,
        "ciphertext_bytes": ciphertext,
        "iv_bytes": iv,
        "auth_tag_bytes": auth_tag,
    }


def compute_payload_hash(ciphertext: bytes, iv: bytes, auth_tag: bytes) -> str:
    """Compute SHA256 hash of payload for PoW binding."""
    return hashlib.sha256(ciphertext + iv + auth_tag).hexdigest()


def solve_pow(nonce: str, difficulty: int, payload_hash: str) -> int:
    """Solve proof-of-work challenge. Returns winning counter."""
    target = 2 ** (256 - difficulty)

    for counter in range(10_000_000):  # Should find solution within this range
        preimage = f"{nonce}{counter:016x}{payload_hash}"
        hash_bytes = hashlib.sha256(preimage.encode()).digest()
        hash_int = int.from_bytes(hash_bytes, "big")

        if hash_int < target:
            return counter

    raise RuntimeError("Failed to solve PoW within iteration limit")


class TestChallenges:
    """Tests for the /challenges endpoint."""

    def test_create_challenge(self, client):
        """Test creating a PoW challenge."""
        test_data = generate_test_data()
        payload_hash = compute_payload_hash(
            test_data["ciphertext_bytes"],
            test_data["iv_bytes"],
            test_data["auth_tag_bytes"],
        )

        response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )

        assert response.status_code == 201
        data = response.json()
        assert "challenge_id" in data
        assert "nonce" in data
        assert "difficulty" in data
        assert data["algorithm"] == "sha256"
        assert len(data["nonce"]) == 64  # 32 bytes as hex

    def test_challenge_invalid_payload_hash(self, client):
        """Test creating a challenge with invalid payload hash."""
        response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": "tooshort", "ciphertext_size": 100},
        )

        assert response.status_code == 422  # Validation error


class TestSecrets:
    """Tests for the /secrets endpoints."""

    def test_create_secret_full_flow(self, client):
        """Test creating a secret with full PoW flow."""
        test_data = generate_test_data()
        payload_hash = compute_payload_hash(
            test_data["ciphertext_bytes"],
            test_data["iv_bytes"],
            test_data["auth_tag_bytes"],
        )

        # Step 1: Get challenge
        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        assert challenge_response.status_code == 201
        challenge = challenge_response.json()

        # Step 2: Solve PoW
        counter = solve_pow(challenge["nonce"], challenge["difficulty"], payload_hash)

        # Step 3: Create secret
        unlock_at = utcnow() + timedelta(hours=1)
        create_response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,
                },
            },
        )

        assert create_response.status_code == 201
        data = create_response.json()
        assert "secret_id" in data
        assert "unlock_at" in data
        assert "created_at" in data

    def test_retrieve_before_unlock(self, client):
        """Test that retrieval before unlock date is rejected."""
        test_data = generate_test_data()
        payload_hash = compute_payload_hash(
            test_data["ciphertext_bytes"],
            test_data["iv_bytes"],
            test_data["auth_tag_bytes"],
        )

        # Get challenge and solve PoW
        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        challenge = challenge_response.json()
        counter = solve_pow(challenge["nonce"], challenge["difficulty"], payload_hash)

        # Create secret with future unlock date
        unlock_at = utcnow() + timedelta(days=1)
        client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,
                },
            },
        )

        # Try to retrieve before unlock
        retrieve_response = client.get(
            "/api/v1/secrets/retrieve",
            headers={"Authorization": f"Bearer {test_data['decrypt_token']}"},
        )

        assert retrieve_response.status_code == 403

    def test_status_check(self, client):
        """Test the non-destructive status check endpoint."""
        test_data = generate_test_data()
        payload_hash = compute_payload_hash(
            test_data["ciphertext_bytes"],
            test_data["iv_bytes"],
            test_data["auth_tag_bytes"],
        )

        # Get challenge and solve PoW
        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        challenge = challenge_response.json()
        counter = solve_pow(challenge["nonce"], challenge["difficulty"], payload_hash)

        # Create secret
        unlock_at = utcnow() + timedelta(hours=1)
        client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,
                },
            },
        )

        # Check status
        status_response = client.get(
            "/api/v1/secrets/status",
            headers={"Authorization": f"Bearer {test_data['decrypt_token']}"},
        )

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["exists"] is True
        assert data["status"] == "pending"
        assert "unlock_at" in data

    def test_invalid_token(self, client):
        """Test that invalid tokens are rejected."""
        response = client.get(
            "/api/v1/secrets/retrieve",
            headers={"Authorization": "Bearer " + "a" * 64},
        )

        assert response.status_code == 404

    def test_edit_page_can_get_status_with_edit_token(self, client):
        """
        The edit page needs to check secret status using the edit token.
        Currently this fails because /secrets/status only accepts decrypt tokens.
        """
        test_data = generate_test_data()
        payload_hash = compute_payload_hash(
            test_data["ciphertext_bytes"],
            test_data["iv_bytes"],
            test_data["auth_tag_bytes"],
        )

        # Get challenge and solve PoW
        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        challenge = challenge_response.json()
        counter = solve_pow(challenge["nonce"], challenge["difficulty"], payload_hash)

        # Create secret
        unlock_at = utcnow() + timedelta(hours=24)
        create_response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,
                },
            },
        )
        assert create_response.status_code == 201

        # The edit page uses the edit token to get status
        # This should work but currently fails
        status_response = client.get(
            "/api/v1/secrets/edit/status",
            headers={"Authorization": f"Bearer {test_data['edit_token']}"},
        )

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["exists"] is True
        assert data["status"] == "pending"
        assert "unlock_at" in data

    def test_pow_challenge_reuse_rejected(self, client):
        """Test that PoW challenges cannot be reused."""
        test_data = generate_test_data()
        payload_hash = compute_payload_hash(
            test_data["ciphertext_bytes"],
            test_data["iv_bytes"],
            test_data["auth_tag_bytes"],
        )

        # Get challenge and solve PoW
        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        challenge = challenge_response.json()
        counter = solve_pow(challenge["nonce"], challenge["difficulty"], payload_hash)

        # Create first secret
        unlock_at = utcnow() + timedelta(hours=1)
        first_response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,
                },
            },
        )
        assert first_response.status_code == 201

        # Try to reuse the same challenge
        test_data2 = generate_test_data()
        second_response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data2["ciphertext"],
                "iv": test_data2["iv"],
                "auth_tag": test_data2["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data2["edit_token"],
                "decrypt_token": test_data2["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,  # Using same payload hash
                },
            },
        )

        assert second_response.status_code == 400
        assert "already used" in second_response.json()["detail"]


class TestValidation:
    """Tests for input validation."""

    def test_invalid_iv_size(self, client):
        """Test that IV must be exactly 12 bytes."""
        test_data = generate_test_data()
        test_data["iv"] = base64.b64encode(secrets.token_bytes(16)).decode()  # Wrong size

        payload_hash = "a" * 64  # Fake hash
        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        challenge = challenge_response.json()

        unlock_at = utcnow() + timedelta(hours=1)
        response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": 0,
                    "payload_hash": payload_hash,
                },
            },
        )

        assert response.status_code == 422
        assert "12 bytes" in str(response.json())

    def test_invalid_auth_tag_size(self, client):
        """Test that auth tag must be exactly 16 bytes."""
        test_data = generate_test_data()
        test_data["auth_tag"] = base64.b64encode(secrets.token_bytes(12)).decode()  # Wrong size

        payload_hash = "a" * 64
        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        challenge = challenge_response.json()

        unlock_at = utcnow() + timedelta(hours=1)
        response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": 0,
                    "payload_hash": payload_hash,
                },
            },
        )

        assert response.status_code == 422
        assert "16 bytes" in str(response.json())

    def test_unlock_date_too_soon(self, client):
        """Test that unlock date must be at least 5 minutes in future."""
        test_data = generate_test_data()
        payload_hash = "a" * 64

        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        challenge = challenge_response.json()

        unlock_at = utcnow() + timedelta(minutes=1)  # Too soon
        response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": 0,
                    "payload_hash": payload_hash,
                },
            },
        )

        assert response.status_code == 422
        assert "5 minutes" in str(response.json())


class TestPowHardening:
    """Tests for PoW binding and difficulty enforcement."""

    def test_payload_hash_must_match_ciphertext(self, client):
        """PoW solved for one payload cannot be used for different payload."""
        # Generate original test data and get challenge
        original_data = generate_test_data()
        original_hash = compute_payload_hash(
            original_data["ciphertext_bytes"],
            original_data["iv_bytes"],
            original_data["auth_tag_bytes"],
        )

        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": original_hash, "ciphertext_size": 100},
        )
        assert challenge_response.status_code == 201
        challenge = challenge_response.json()

        # Solve PoW for original payload
        counter = solve_pow(challenge["nonce"], challenge["difficulty"], original_hash)

        # Try to create secret with DIFFERENT ciphertext but same PoW proof
        different_data = generate_test_data()
        unlock_at = utcnow() + timedelta(hours=1)

        response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": different_data["ciphertext"],  # Different!
                "iv": different_data["iv"],
                "auth_tag": different_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": different_data["edit_token"],
                "decrypt_token": different_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": original_hash,  # Original hash in proof
                },
            },
        )

        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"].lower()

    def test_overpay_difficulty_allowed(self, client):
        """Can use high-difficulty challenge for smaller payload (overpay is OK)."""
        # Generate small payload
        small_data = generate_test_data()
        payload_hash = compute_payload_hash(
            small_data["ciphertext_bytes"],
            small_data["iv_bytes"],
            small_data["auth_tag_bytes"],
        )

        # Request challenge claiming slightly larger size to get +1 difficulty
        # 100KB = base + 1 bit difficulty
        challenge_response = client.post(
            "/api/v1/challenges",
            json={
                "payload_hash": payload_hash,
                "ciphertext_size": 100_000,  # Claim 100KB, actual is ~100 bytes
            },
        )
        assert challenge_response.status_code == 201
        challenge = challenge_response.json()

        # Difficulty should be base + 1 for 100KB
        assert challenge["difficulty"] == 18 + 1  # Base + 1 for 100KB

        # Solve the slightly harder challenge (still fast enough for tests)
        counter = solve_pow(challenge["nonce"], challenge["difficulty"], payload_hash)

        # Submit with actual small data - should succeed (overpay OK)
        unlock_at = utcnow() + timedelta(hours=1)
        response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": small_data["ciphertext"],
                "iv": small_data["iv"],
                "auth_tag": small_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": small_data["edit_token"],
                "decrypt_token": small_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,
                },
            },
        )

        assert response.status_code == 201

    def test_challenge_not_burned_on_validation_failure(self, client):
        """Challenge should not be marked used if secret creation fails validation."""
        test_data = generate_test_data()
        payload_hash = compute_payload_hash(
            test_data["ciphertext_bytes"],
            test_data["iv_bytes"],
            test_data["auth_tag_bytes"],
        )

        # Get challenge
        challenge_response = client.post(
            "/api/v1/challenges",
            json={"payload_hash": payload_hash, "ciphertext_size": 100},
        )
        challenge = challenge_response.json()
        counter = solve_pow(challenge["nonce"], challenge["difficulty"], payload_hash)

        # Try to create secret with invalid unlock date (too soon)
        unlock_at = utcnow() + timedelta(minutes=1)  # Invalid - too soon
        first_response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,
                },
            },
        )
        assert first_response.status_code == 422  # Validation error

        # Now try again with valid unlock date - should work because challenge wasn't burned
        valid_unlock_at = utcnow() + timedelta(hours=1)
        second_response = client.post(
            "/api/v1/secrets",
            json={
                "ciphertext": test_data["ciphertext"],
                "iv": test_data["iv"],
                "auth_tag": test_data["auth_tag"],
                "unlock_at": valid_unlock_at.isoformat(),
                "edit_token": test_data["edit_token"],
                "decrypt_token": test_data["decrypt_token"],
                "pow_proof": {
                    "challenge_id": challenge["challenge_id"],
                    "nonce": challenge["nonce"],
                    "counter": counter,
                    "payload_hash": payload_hash,
                },
            },
        )
        assert second_response.status_code == 201
