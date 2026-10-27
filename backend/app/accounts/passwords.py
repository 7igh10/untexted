from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.profiles import RFC_9106_LOW_MEMORY

_password_hasher = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)


def hash_password(password: str) -> str:
    """Return an Argon2id hash using the RFC 9106 low-memory profile."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


# Used to reduce timing differences for unknown usernames.
DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")