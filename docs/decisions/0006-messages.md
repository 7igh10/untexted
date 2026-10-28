# ADR 0006: Messages and Structured Message Payloads

## Status

Accepted

## Context

Untexted needs persistent one-to-one messages in existing private
conversations. Messages must support emoji sequences and a small set of
structured interactive types without introducing free-form text as the primary
format. The design must remain minimal, extensible, and consistent with the
modular monolith and PostgreSQL-first architecture.

## Decision

Store all message types in one `messages` table. Each row contains:

- conversation and sender identifiers;
- message `type`;
- `schema_version`;
- `payload` as PostgreSQL `JSONB`;
- optional `reply_to_message_id`;
- `created_at`.

The server assigns `schema_version`; clients cannot choose it.

Payloads are validated by Pydantic before persistence. The initial supported
types are:

- `emoji`
- `template`
- `location`
- `time`
- `link`

The `template` type supports only a small fixed set of templates:
`greeting`, `mood_question`, and `meeting_invitation`. Template parameters are
validated per template instead of allowing an unbounded generic dictionary.

Emoji messages use moderate Unicode validation. They allow composite emoji,
ZWJ sequences, variation selectors, and skin-tone modifiers, while rejecting
letters, whitespace, control characters, and oversized content.

Time messages require a timezone-aware `occurs_at`. An optional IANA timezone
preserves the original local scheduling context.

For `time` and `meeting_invitation`, `occurs_at` is an absolute instant and
must include a timezone. `timezone`, when present, is a valid IANA identifier
for display context. It may describe the same absolute instant in a different
zone. The server does not silently convert one field into the other.

A reply references another message through `reply_to_message_id`. The database
enforces that the referenced message exists; the service additionally verifies
that it belongs to the same conversation.

## Access rules

- Reading history requires conversation participation.
- Reading remains available after friendship ends.
- Sending requires active friendship between conversation participants.
- Existing conversations and message history are preserved after friendship
  ends.
- Restored friendship reuses the same conversation and history.

## Pagination

History uses cursor-based pagination ordered by `(created_at, id)`. The default
page size is 50 and the maximum is 100. Pages are returned in chronological
order with an opaque `next_cursor`.

## Consequences

### Positive

- One table supports all current and future message types.
- JSONB keeps the schema extensible without frequent migrations.
- Pydantic validation prevents invalid structured payloads.
- Cursor pagination avoids unbounded history loading.
- Existing history remains available after friendship changes.

### Trade-offs

- JSONB payloads are less constrained by PostgreSQL than fully normalized
  columns.
- Emoji validation is heuristic and does not attempt full Unicode Emoji
  correctness.
- Reply integrity across conversations is enforced by service logic rather than
  a composite database key.

## Future requirements

- Message deletion and editing.
- Reactions.
- Delivery and read states.
- WebSocket delivery.
- Friendship removal coordination with message sending.
- Additional message types and template parameters.
