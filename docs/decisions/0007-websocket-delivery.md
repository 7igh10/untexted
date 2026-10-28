# ADR 0007: WebSocket Delivery for Private Conversations

## Status

Accepted

## Context

Untexted already stores messages in PostgreSQL and delivers them through an
HTTP API. The MVP also needs live delivery while a conversation is open,
without introducing Redis, message brokers, frontend code, or a separate
service.

## Decision

Use FastAPI/Starlette WebSocket connections for live delivery only.

- The endpoint is `/conversations/{conversation_id}/ws`.
- Authentication uses the existing session cookie.
- The server checks conversation participation before accepting the
  connection.
- An in-memory `ConnectionManager` maps a conversation to its active
  WebSocket connections.
- HTTP message creation remains the only way to create a message.
- After a successful HTTP send, the server broadcasts a `message` event to all
  active connections for that conversation.
- WebSocket accepts only `{"type": "ping"}` from clients.
- Missed events are not replayed; clients load them through the existing
  history endpoint.

Origin handling follows the existing `ALLOWED_ORIGINS` and CSRF strictness
configuration. Unauthorized or inaccessible connections are closed before
acceptance.

## Consequences

### Positive

- Live delivery requires no new infrastructure.
- Message creation logic remains in one place.
- Existing authorization and friendship rules are reused.
- Disconnected clients can recover through cursor-based history.

### Trade-offs

- Delivery works only within one backend instance.
- There is no guaranteed delivery or event queue.
- Connection state is lost on process restart.
- Long-lived WebSocket connections hold a database session.

## Out of scope

- Redis or external brokers.
- WebSocket message creation.
- Delivery and read receipts.
- Reconnect replay.
- Frontend implementation.
