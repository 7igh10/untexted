# ADR 0003: Session-Based Authentication

## Status

Accepted

## Context

Untexted is a browser application with a future WebSocket messaging layer. It
needs login, logout, current-user lookup, and protected endpoints. The backend
already stores Argon2id password hashes and uses PostgreSQL as the source of
truth.

## Decision

Use server-side sessions stored in PostgreSQL. The browser stores only an
opaque high-entropy token in an `HttpOnly` cookie. PostgreSQL stores only the
SHA-256 hash of that token, along with user ID and expiration time.

Session lifetime is 14 days. Sliding renewal occurs when less than 24 hours
remain, extending `expires_at` by 14 days and updating the cookie `Max-Age`.

JWT was not chosen for the MVP because revocation, logout, token rotation, and
browser storage are more complex and riskier than an opaque server-side
session. Redis was not added; PostgreSQL remains the authoritative store.

## Consequences

### Positive

- Immediate logout and session revocation.
- No client-side access to the session token.
- No Redis or additional infrastructure.
- Compatible with future WebSocket authentication through the session cookie.
- Multiple independent sessions per user are supported.

### Trade-offs

- Each protected request performs a session lookup.
- The in-memory rate limiter is process-local and resets on restart.
- `SameSite=Lax` reduces but does not fully prevent CSRF; Origin/Referer
  checks are also used.
- Cookie `Secure` must be enabled in production through `COOKIE_SECURE=true`.

### Future requirements

- Mandatory 2FA for privileged roles.
- Revocation of all sessions on password change or suspected compromise.
- Stronger abuse protection for administrative accounts.
- Email verification and password reset as separate future features.
