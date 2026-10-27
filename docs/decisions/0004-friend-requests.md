# ADR 0004: Friend Requests and Friendships

## Status

Accepted

## Context

Untexted needs basic contact management for the MVP. Two registered users must
be able to send, accept, and reject friend requests, and view their friends.
The design must support future friend removal without notifications.

## Decision

Use two PostgreSQL tables:

- `friend_requests` stores directed requests with statuses `pending`,
  `accepted`, and `rejected`.
- `friendships` stores one normalized row per friendship, with `user_id <
  friend_id`.

Uniqueness and integrity are enforced by PostgreSQL:
- `UNIQUE (requester_id, recipient_id)` prevents duplicate directed requests.
- A partial unique index prevents two pending requests between the same pair
  in either direction.
- `UNIQUE (user_id, friend_id)` plus `CHECK (user_id < friend_id)` prevents
  duplicate friendships.

Mutual pending requests are automatically converted into one friendship.

## Consequences

### Positive

- Friendship state is explicit and easy to query.
- Future friend removal only deletes a `friendships` row.
- Constraints protect against races and duplicate data.
- Public user data remains separate from relationship state.

### Trade-offs

- Two tables and transactional service logic are more complex than a single
  status column.
- Friendship checks require a normalized user ID pair.
- Ignored requests remain pending indefinitely.

### Future requirements

- Friend removal.
- Profile visibility based on friendship.
- System events in conversations.
- Filtering search results by existing friendship.
