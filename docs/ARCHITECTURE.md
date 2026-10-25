# Untexted — Architecture

## 1. Purpose

This document describes the initial technical architecture of Untexted, the responsibilities of its main components, and the principles that will guide its future evolution.

The architecture should support the initial MVP while allowing the product to grow without introducing unnecessary operational complexity.

## 2. Architectural Principles

The project follows these principles:

- Modular design with clearly defined responsibilities.
- Secure handling of accounts, messages, and personal data.
- Versioned and extensible message schemas.
- Persistent storage for important application data.
- Automated testing and reproducible development environments.
- Observable and diagnosable application behavior.
- Incremental evolution toward independently deployable services when justified by actual requirements.

The initial architecture will use a modular monolith for the backend, supported by separate infrastructure components.

Microservices will be introduced only when there is a clear technical or operational reason.

## 3. Initial Technology Stack

| Component | Technology | Responsibility |
|---|---|---|
| Frontend | React and TypeScript | User interface |
| Backend | Python and FastAPI | API and application logic |
| Primary database | PostgreSQL | Persistent application data |
| Cache and temporary coordination | Redis | Selected caching and temporary data |
| Real-time communication | WebSocket | Real-time message delivery |
| Reverse proxy | Nginx | HTTP routing and entry point |
| Containerization | Docker Compose | Local development environment |
| Continuous integration | GitHub Actions | Automated checks and tests |
| Backend testing | pytest | Automated backend tests |

Additional technologies may be introduced when required by specific features.

## 4. High-Level Component Architecture

### 4.1 Frontend

The frontend is responsible for:

- Rendering user profiles and conversations.
- Providing emoji selection and message composition.
- Displaying structured messages and contextual responses.
- Managing client-side navigation and interface state.
- Communicating with the backend through HTTP and WebSocket connections.

The frontend must not be trusted to enforce security or authorization rules.

### 4.2 Backend API

The backend is responsible for:

- Authentication and authorization.
- User profiles and contact relationships.
- Conversation and message management.
- Validation of structured messages.
- Contextual response rules.
- Invitation workflows.
- Persistent data access.
- Application-level security controls.

The backend will initially be organized as a modular monolith.

Proposed logical modules:

- Accounts.
- Profiles.
- Contacts.
- Messaging.
- Events.

These modules will have clear responsibilities and explicit dependencies.

They will initially run within one backend application rather than as separate network services.

### 4.3 PostgreSQL

PostgreSQL is the source of truth for persistent application data.

It will store data such as:

- User accounts.
- User profiles.
- Contact relationships.
- Conversations and conversation membership.
- Messages and their structured payloads.
- Invitations and invitation statuses.

The database schema will evolve through version-controlled migrations.

Important application data must not exist exclusively in Redis.

### 4.4 Redis

Redis will be used selectively for:

- Caching data when justified.
- Rate-limiting counters.
- Temporary coordination data.
- Future coordination of WebSocket connections or background tasks, if required.

Redis is not the primary database for message history.

The initial implementation should not introduce caching without a clear use case.

The application must remain correct if cached data expires or is removed.

### 4.5 Nginx

Nginx will act as the application’s HTTP entry point.

It may route requests to the frontend and backend and support WebSocket connections.

The backend and database should not expose unnecessary public ports.

Production deployment must use HTTPS.

### 4.6 Background Worker

A separate worker may be introduced when the application requires asynchronous or scheduled processing.

Potential future responsibilities include:

- Email delivery.
- Event reminders.
- Notification processing.
- Media processing.
- Other long-running tasks.

The worker’s implementation and task queue will be selected according to the actual requirements.

Scheduled reminders are not part of the initial MVP.

## 5. Messaging Architecture

### 5.1 Message Model

Messages must be represented as structured application data rather than as emoji strings alone.

A message may contain:

- A unique identifier.
- Conversation identifier.
- Sender identifier.
- Message type.
- Schema version.
- Structured payload.
- Creation timestamp.

The exact database schema will be defined during backend design.

### 5.2 Versioned Message Types

The messaging system must support versioned message schemas.

Initial types may include:

- Emoji sequence.
- Link.
- Question with predefined responses.
- Invitation.
- Contextual response.

The exact set of message types supported by the initial release is defined in the MVP scope document.

Each message type must define its expected payload and validation rules.

The visual representation of a message must remain separate from its underlying data model.

This allows the interface to evolve without changing the meaning of previously stored messages.

### 5.3 Contextual Responses

Contextual response options depend on the original message type and its intended meaning.

Examples:

- A greeting may offer greeting responses.
- A well-being question may offer mood-related responses.
- An invitation may offer acceptance, rejection, or an alternative proposal.

The backend must validate that a response is permitted for the original message.

The client interface must not be the sole authority for determining which responses are valid.

### 5.4 Real-Time Delivery

WebSocket connections will be used for real-time communication.

The backend must authenticate WebSocket connections and verify conversation membership before allowing access to messages.

Persisted messages will be stored in PostgreSQL.

The application should support reconnection and retrieval of messages missed while a client was disconnected.

Message delivery and persistence behavior will be specified and tested during implementation.

## 6. Data Ownership and Consistency

PostgreSQL is the authoritative source for persistent application state.

Redis may contain temporary or derived data, but the loss of that data must not corrupt persistent records.

Operations that change important state, such as accepting an invitation, must be validated by the backend and persisted consistently.

The initial system should prefer straightforward transactional behavior over distributed transactions.

## 7. Security Boundaries

Security controls must be enforced by the backend.

The initial implementation must address:

- Password hashing.
- Email verification.
- Authentication and authorization.
- Conversation membership checks.
- Input and payload validation.
- Rate limiting.
- Protection against unauthorized access to private resources.
- Secure handling of configuration and secrets.

Secrets must not be committed to the repository.

The application must not rely on hidden interface elements as an access-control mechanism.

## 8. Development and Deployment

The initial development environment will use Docker Compose.

The local environment should provide reproducible startup and test procedures.

The project will evolve toward:

- Automated CI checks.
- Database migrations.
- Health checks.
- Structured logging.
- Production deployment with HTTPS.
- Automated deployment procedures.
- Backups and recovery documentation.

Production secrets and local development configuration must be handled separately.

## 9. Testing and Observability

Automated tests should cover critical business behavior, including:

- Authentication and authorization.
- Contact management.
- Message validation.
- Contextual response validation.
- Message persistence.
- Invitation state transitions.

The application should expose health information suitable for operational checks.

Structured logs and metrics will be introduced incrementally to support troubleshooting and reliability.

## 10. Evolution Toward Microservices

The initial backend will remain a modular monolith.

A module may be considered for extraction into a separate service when there is a demonstrated need, such as:

- Independent scaling requirements.
- A distinct deployment lifecycle.
- A meaningful security or operational boundary.
- A separate workload with different resource requirements.
- A clear ownership or maintenance benefit.

Potential future service boundaries include messaging, notifications, and media processing.

Each extracted service must have a defined responsibility and communication contract.

The project must not introduce microservices solely to increase the number of containers or technologies.

## 11. Infrastructure Evolution

Docker Compose is the initial orchestration mechanism.

Ansible may later be used to automate server configuration and deployment.

Monitoring, alerting, backups, and recovery procedures will be introduced as the application becomes deployable outside the local environment.

Kubernetes and more advanced infrastructure automation are future learning and deployment goals, not requirements for the first MVP.

## 12. Open Architectural Decisions

The following decisions require further investigation before implementation:

- Session management and authentication details.
- Email delivery provider.
- Message payload schemas.
- Database schema and migration strategy.
- WebSocket authentication and reconnection behavior.
- Redis usage and eviction policy.
- Background task execution mechanism.
- Media storage strategy.
- Production deployment topology.

These decisions should be documented when their requirements are sufficiently clear.

## 13. Architectural Decision Rule

Every significant architectural choice should have a clear purpose and documented trade-offs.

The simplest solution that satisfies current requirements should be preferred, provided that it does not prevent reasonable future evolution.