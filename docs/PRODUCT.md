# Untexted - Product Overview

## 1. Vision

Untexted is a social platform for expressive communication without conventional free-form text as the primary messaging format.

Users communicate through emoji sequences and structured messages, share activities and events, build personal spaces, and connect with people who have similar interests.

The long-term vision is to develop Untexted into a broader social platform with messaging, communities, personal profiles, digital pets, events, games, and extensible interactive features.

## 2. Product Principles

- Emoji-first communication.
- Structured and extensible message formats.
- Privacy and user control over personal information.
- Responsive web experience across desktop and mobile devices.
- Secure handling of accounts, messages, and user-generated content.
- Incremental development with measurable, testable results.
- Architecture that supports future growth without unnecessary complexity.

## 3. Initial MVP

The first version should include:

- User registration and authentication.
- Personal profiles.
- Contact management.
- One-to-one conversations.
- Real-time messaging.
- Emoji-sequence messages.
- Basic structured message types.
- Persistent message history.
- A responsive web interface.
- Contextual responses for supported message types.

## 4. Future Features

Features considered for later iterations:

- Groups and communities.
- Interests and discovery.
- Personal and public events.
- Digital pets and customizable habitats.
- Achievements and internal virtual currency.
- AI-assisted conversion of conventional text into emoji sequences.
- AI-assisted interpretation of emoji messages.
- Additional interactive and game-like experiences.

These features are not part of the initial MVP unless explicitly added to its scope.

## 5. Communication Model

Conventional free-form text is not the primary message format in Untexted.

Messages should use explicit, versionable schemas so that new message types can be introduced without redesigning the entire messaging system.

Initial message types may include:

- Emoji sequences.
- Links.
- Questions with predefined response options.
- Invitations to activities or events.
- Structured responses to previously received messages.

AI-assisted text conversion is a future feature and must not be assumed to exist in the initial implementation.

## 6. Initial Technology Direction

- Frontend: React and TypeScript.
- Backend: Python and FastAPI.
- Primary database: PostgreSQL.
- Cache and temporary coordination data: Redis where justified.
- Real-time communication: WebSocket.
- Containerization: Docker and Docker Compose.
- Reverse proxy: Nginx.
- Continuous integration: GitHub Actions.
- Automated tests and documented development workflows.

The initial application should use a modular architecture. Independently deployable services may be introduced when justified by operational or product requirements.

## 7. Non-Functional Requirements

The project should evolve toward:

- Secure authentication and authorization.
- Input validation and protection against common web vulnerabilities.
- Automated testing.
- Reproducible local development.
- Structured application logs.
- Health checks and operational metrics.
- Documented deployment and recovery procedures.
- Database migrations and backup procedures.
- Clear configuration and secret-management practices.

Specific performance and availability targets will be defined when the system requirements become clearer.

## 8. Development Approach

Development proceeds in small, verifiable iterations.

Every significant change should have:

- A clear purpose.
- Defined acceptance criteria.
- Appropriate tests.
- Documented architectural decisions when needed.
- A reviewable Git diff.

The architecture must serve the product rather than introduce complexity for its own sake.