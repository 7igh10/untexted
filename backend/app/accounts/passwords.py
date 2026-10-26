from argon2 import PasswordHasher
from argon2.profiles import RFC_9106_LOW_MEMORY

_password_hasher = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)


def hash_password(password: str) -> str:
    """Return an Argon2id hash using the RFC 9106 low-memory profile."""
    return _password_hasher.hash(password)
