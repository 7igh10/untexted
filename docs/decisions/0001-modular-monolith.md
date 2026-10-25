# ADR 0001: Start with a Modular Monolith

## Status

Accepted

## Context

Untexted is an early-stage social communication platform.

The initial MVP includes authentication, user profiles, contacts, private conversations, real-time messaging, structured messages, and event invitations.

The project is developed as a portfolio project and must remain practical to build, test, deploy, and maintain.

Starting with independently deployed microservices would introduce additional operational complexity before the application has demonstrated a need for it.

## Decision

The initial backend will be implemented as a modular monolith.

The backend will have clearly separated logical modules:

- Accounts.
- Profiles.
- Contacts.
- Messaging.
- Events.

These modules will run within one backend application and initially use one PostgreSQL database.

Frontend, backend, database, and reverse proxy components may run in separate containers.

Redis and background workers will be introduced only when justified by concrete requirements.

## Consequences

### Positive

- Simpler local development and deployment.
- Easier testing of business logic.
- Straightforward database transactions.
- Fewer operational components to maintain.
- Clear logical boundaries that support future evolution.

### Trade-offs

- Backend modules initially share a deployment lifecycle.
- Module boundaries must be maintained through code organization and dependency rules.
- Independent scaling of individual backend modules is not available initially.

## Reconsideration Criteria

The decision may be revisited if a module develops a demonstrated need for independent scaling, deployment, security boundaries, or a substantially different operational workload.

Microservices will not be introduced solely to increase the number of technologies or containers.