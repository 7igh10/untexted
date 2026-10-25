# Untexted — MVP Scope

## 1. MVP Goal

The goal of the MVP is to deliver a usable social communication platform where users can communicate primarily through emoji sequences and structured interactive messages.

The MVP must demonstrate a complete user journey: registration, contact management, real-time messaging, event invitations, and personal scheduling.

## 2. Authentication and Accounts

The MVP includes:

- Email and password registration.
- Email address verification.
- Login and logout.
- Secure password hashing.
- Password recovery.
- Rate limiting for authentication endpoints.
- Basic anti-abuse protections.
- Authorization checks for protected resources.

External identity providers are out of scope for the initial release.

## 3. User Profiles

The MVP includes:

- A unique user identifier.
- A unique public username.
- A display name.
- A basic avatar.
- Basic profile settings.
- Privacy-conscious defaults.

Advanced avatar customization, digital pets, achievements, and profile decoration are future features.

## 4. Contacts

The MVP includes:

- Finding users by username.
- Sending contact requests.
- Accepting and rejecting requests.
- Removing contacts.
- Viewing the contact list.

The application must prevent unauthorized access to private user information.

## 5. Messaging

### 5.1 Emoji Messages

Users can:

- Select standard Unicode emoji.
- Search for emoji.
- Compose emoji sequences.
- Preview a message before sending it.
- Send and receive messages in real time.
- View message history.

### 5.2 Emoji Composer

The application should support deterministic conversion of supported text characters into an emoji-based representation.

The initial implementation should:

- Support Latin letters and digits where a suitable representation exists.
- Define and document deterministic conversion rules.
- Display a preview before sending.
- Allow users to edit the resulting emoji sequence.
- Handle unsupported characters predictably.

Support for the Russian alphabet and additional character sets is planned for a later iteration.

AI-assisted semantic conversion of conventional text into emoji sequences is out of scope for the initial release.

### 5.3 Structured Messages

The application must support extensible, versioned message types.

Initial message types include:

- Emoji sequences.
- Links.
- Questions with predefined response options.
- Invitations to activities or events.
- Structured responses to previously received messages.

Each structured message must contain its type, schema version, and validated payload.

The visual emoji representation must not be the only source of information about a message’s meaning or behavior.

### 5.4 Contextual Responses

The application should support contextual response options based on the message type and its intended meaning.

For example:

- Greetings may offer greeting responses.
- Questions about well-being may offer emoji representing different moods.
- Invitations may offer acceptance, rejection, or a proposal for an alternative time.
- Other supported message types may define their own response options.

The initial implementation should support a limited set of scenarios:

1. Greetings.
2. Questions about well-being.
3. Basic invitations.
4. Acceptance and rejection of invitations.

The architecture must allow additional message types and response options to be introduced without redesigning the entire messaging system.

The backend must validate contextual responses against the original message type and the recipient’s permissions.

### 5.5 Real-Time Delivery

The application must support real-time delivery through WebSocket connections.

The backend must verify the authenticated user’s identity and permissions before allowing access to a conversation.

Message history must be persisted in PostgreSQL.

The system should handle reconnects without silently losing persisted messages.

## 6. Event Invitations

The MVP includes a basic invitation workflow.

An invitation may contain:

- Event title or type.
- Date and time.
- Optional location.
- Optional link.
- Invitation status.
- Sender and recipient.

Recipients can accept or decline invitations.

Users must be able to view their invitations and their current statuses.

The sender may cancel an invitation. The recipient may change their response while the invitation remains active.

A full personal calendar, automatic scheduling, and scheduled reminders are out of scope for the initial MVP.

## 7. Personal Schedule

A full personal calendar is out of scope for the initial MVP.

The MVP only provides access to invitations and their statuses, as described in the Event Invitations section.

The following features are planned for later releases:

- A personal calendar interface.
- Automatic addition of accepted invitations to a calendar.
- Scheduled reminders.
- Event visibility management.
- Recurring events.
- Synchronization with external calendar providers.

## 8. Media

Image uploads and other media attachments are out of scope for the initial release.

The message model should remain extensible so that media attachments can be introduced later.

Links may be supported as structured messages, with appropriate URL validation and safe rendering.

## 9. Frontend

The MVP includes:

- A responsive web interface.
- Registration and login screens.
- User profiles.
- Contact management.
- A conversation list.
- A conversation view.
- An emoji picker and composer.
- Structured invitation cards.
- A list of invitations and their statuses.

The interface should support desktop and mobile browsers.

## 10. Infrastructure

The initial local development environment should include:

- React and TypeScript frontend.
- Python and FastAPI backend.
- PostgreSQL.
- Docker Compose.
- Nginx reverse proxy.
- Automated backend tests.
- Automated frontend checks.
- GitHub Actions CI workflow.

Additional infrastructure components, such as Redis or a background worker, may be introduced when a specific requirement justifies them.

The initial application should run as a modular monolith. Logical backend modules do not need to be deployed as separate services.

## 11. Security and Reliability

The MVP should include:

- Input validation.
- Authentication and authorization checks.
- Rate limiting.
- Secure password storage.
- Secret management through environment configuration.
- Database migrations.
- Health checks.
- Structured application logging.
- Automated tests for critical user journeys.
- Documented local setup and recovery procedures.

Secrets must not be committed to the repository.

## 12. Acceptance Criteria

The MVP is considered usable when:

1. A user can register and verify their email address.
2. A user can log in and access their profile.
3. Users can find one another and establish contact.
4. A user can open a private conversation.
5. Users can exchange emoji messages in real time.
6. Messages remain available after application restarts.
7. A user can send an event invitation.
8. The recipient can accept or decline the invitation.
9. Users can view their invitations and their current statuses.
10. Private conversations and invitations cannot be accessed by unauthorized users.
11. The application can be started locally using documented instructions.
12. Automated tests cover the main authentication, messaging, and invitation flows.

## 13. Out of Scope

The following features are planned for future releases:

- Full personal calendar and scheduling interface.
- Scheduled reminders and advanced notifications.
- Groups and communities.
- Advanced interest-based discovery.
- Digital pets and habitat customization.
- Virtual currency and achievements.
- AI-assisted semantic emoji conversion.
- AI interpretation of emoji sequences.
- Russian alphabet support in the Emoji Composer.
- Image and video uploads.
- Audio hosting.
- Third-party calendar synchronization.
- External social login providers.
- Custom emoji packs with a unified visual style.
- Independently deployed microservices unless justified by demonstrated requirements.
- Kubernetes-based deployment.

## 14. Scope Management

The MVP is intentionally limited to the smallest set of features that demonstrates the core communication experience.

New features should be added only after reviewing their user value, implementation cost, security implications, and effect on delivery.