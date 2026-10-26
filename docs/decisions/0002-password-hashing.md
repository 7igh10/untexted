# ADR 0002: Password Hashing

## Status

Accepted

## Context

Untexted must store user passwords securely. Passwords must never be stored in
plaintext or protected with custom cryptography. The implementation should use
a maintained library, a current password-hashing algorithm, and as few direct
dependencies as practical.

## Decision

Use Argon2id through `argon2-cffi` for password hashing. The hasher is
configured with the library's RFC 9106 low-memory profile: 64 MiB of memory,
3 iterations, parallelism 4, a 16-byte random salt, and a 32-byte hash.

The encoded Argon2id hash is stored in `users.password_hash` as
`varchar(255)`. The plaintext password is not persisted, logged, or returned by
the API. The password hash is excluded from API response schemas and from the
model's representation.

Password verification and rehashing will be introduced with login support. The
stored PHC string contains the algorithm and parameters needed for future
verification.

## Consequences

### Positive

- Argon2id is a current, memory-hard password-hashing algorithm.
- The salt and parameters are generated and encoded by a maintained library.
- Only one direct runtime dependency is added: `argon2-cffi`.
- The stored format supports future parameter upgrades and rehashing.

### Trade-offs

- Argon2id requires more memory per hash than bcrypt or PBKDF2.
- Password hashing is CPU and memory intensive, so authentication endpoints
  will need rate limiting and operational limits as the product grows.
- The current registration schema has no login flow, so verification is not yet
  exposed by the application.
