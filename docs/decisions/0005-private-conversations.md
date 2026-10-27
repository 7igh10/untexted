# ADR 0005: Private One-to-One Conversations

## Status

Accepted

## Context

Untexted needs private one-to-one conversations between users. The initial
implementation must stay minimal, preserve PostgreSQL as the source of truth,
and avoid messages, WebSockets, groups, or premature abstractions.

## Decision

Represent a private conversation with a `conversations` table containing two
normalized participant columns:

- `user_one_id`
- `user_two_id`
- `CHECK (user_one_id < user_two_id)`
- `UNIQUE (user_one_id, user_two_id)`

This guarantees at most one conversation per unordered user pair. A separate
index on `user_two_id` supports listing conversations by either participant.

A conversation is created only by an explicit user request. Creating a
conversation requires an active friendship at creation time. Reading an
existing conversation does not require the users to remain friends.

If the friendship later ends:

- the conversation remains available to both participants;
- future message sending will be restricted to current friends;
- if friendship is restored, the existing conversation is reused.

For the future messaging stage, sending messages will be allowed only between
current friends. After friendship ends, new messages are prohibited; after
friendship is restored, sending messages is allowed again in the same
conversation. Privacy settings may later extend these rules.

## API

- `POST /conversations` creates a conversation or returns the existing one.
- `GET /conversations` lists the current user's conversations.
- `GET /conversations/{conversation_id}` returns one conversation if the
  current user participates in it.

Repeated creation is idempotent and does not create a duplicate conversation.

## Consequences

### Positive

- The pair uniqueness is enforced by PostgreSQL, not only by Python checks.
- Existing conversations survive friendship removal.
- The model is simple and directly supports future messages.
- No automatic conversation creation is introduced.

### Trade-offs

- Conversation participants are fixed to exactly two users.
- Group chats are out of scope for the MVP.
- Concurrent friendship removal is not implemented yet and will require a
  separate synchronization decision when that feature is added.

## Out of scope

- Messages and message history.
- WebSocket delivery.
- Group chats.
- Conversation deletion or archiving.
- Privacy settings.
- Relationship events.
