from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Configure Argon2id with secure parameters
# time_cost=3, memory_cost=65536 (64MB), parallelism=4
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_token(token: str) -> str:
    """Hash a token using Argon2id."""
    return ph.hash(token)


def verify_token(token: str, token_hash: str) -> bool:
    """Verify a token against its Argon2id hash."""
    try:
        ph.verify(token_hash, token)
        return True
    except VerifyMismatchError:
        return False
