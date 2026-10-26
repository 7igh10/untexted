# AGENTS.md

Instructions for coding agents working in this repository.

## Communication and language

- Communicate with the user in Russian by default unless the user requests another language.
- Keep source code, identifiers, filenames, code comments, commit messages, and technical documentation in English by default.
- Explain technical decisions, implementation details, errors, and test results to the user in Russian.
- Keep code examples and command output unchanged when explaining them.

## Read before changing behavior

- Read [README.md](README.md), [docs/PRODUCT.md](docs/PRODUCT.md), [docs/MVP.md](docs/MVP.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and relevant records in [docs/decisions/](docs/decisions/).
- [docs/MVP.md](docs/MVP.md) defines the current MVP scope. [docs/PRODUCT.md](docs/PRODUCT.md) describes the broader product direction. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and accepted ADRs define technical constraints.
- If documents conflict, surface the conflict and ask rather than silently choosing one. Keep documentation and decision records current when behavior or architecture changes.

## Product scope

Untexted is an emoji-first social platform. Communication uses emoji sequences and explicitly defined structured message types; conventional free-form text is not the primary format.

The MVP includes:

- Registration, login, email verification, password recovery, rate limiting, and profiles.
- Contacts and one-to-one private conversations.
- Real-time messaging with persistent history.
- An emoji composer for supported Latin letters and digits.
- Versioned structured messages and contextual responses.
- Basic event invitations: send, accept or decline, view status, and cancel. Recipients may change their response while an invitation remains active.

Out of scope unless explicitly approved:

- Free-form text messaging.
- A full personal calendar, reminders, recurring events, automatic scheduling, and calendar synchronization.
- Groups and communities, media uploads, AI conversion or interpretation, Russian composer support, external identity providers, digital pets, achievements, virtual currency, microservices, and Kubernetes.

Links may be implemented as a structured message type only when consistent with the existing MVP documentation. Do not expand scope or implement future features opportunistically.

## Stack and architecture

- Frontend: React and TypeScript. Backend: Python and FastAPI. Database: PostgreSQL as the source of truth. Real-time delivery: WebSockets. Entry point: Nginx. Local environment: Docker Compose. CI: GitHub Actions. Backend tests: pytest.
- Use Redis only when a concrete requirement justifies it. Never make Redis authoritative for persistent data, and do not add caching without a clear use case.
- The backend is a modular monolith with logical modules: Accounts, Profiles, Contacts, Messaging, and Events. Keep module boundaries explicit and use one PostgreSQL database.
- Do not introduce premature microservices, extra services, or unnecessary infrastructure. Extract a module only for a demonstrated scaling, deployment, security, or workload need.
- The frontend is untrusted for security decisions. The backend enforces authentication, authorization, and validation.

## Structured messages

- Store messages as structured data with a type, schema version, validated payload, identifiers, and timestamp. Do not rely on an emoji string as the only source of a message's meaning.
- Validate payloads per message type on the server. Validate contextual responses against the original message type and the recipient's permissions.
- Version schemas deliberately: prefer additive changes, use a new version for breaking changes, and never silently reuse existing type or version semantics.
- Exact payload and database schemas are undecided. Define and document them when implementing the relevant feature; do not invent broad schema changes without need.

## Security

- Validate all external input at trust boundaries: HTTP input, WebSocket frames, structured payloads, URLs, and identifiers.
- Enforce authentication and authorization server-side for every protected resource, including conversation membership, message access, invitation sender and recipient actions, and WebSocket subscriptions.
- Use secure password hashing through a maintained, established library. Select a secure algorithm when implementing; never use plaintext or custom cryptography, and do not lock in an algorithm here.
- Do not choose an authentication or session mechanism, email provider, or detailed message payload schema in this file. Use secure defaults and document significant decisions in `docs/decisions/`.
- Never commit secrets, credentials, tokens, or real environment values. Use environment configuration and commit only placeholder `.env.example` values. Keep secrets out of logs, tests, fixtures, and error messages.
- Use parameterized queries or established ORM patterns, safe output rendering, generic authentication errors, and rate limiting on authentication endpoints.

## Code quality and tests

- Make the smallest coherent change. Match existing structure and naming, and avoid unrelated refactors and formatting churn.
- Add or update tests for behavior changes, especially authentication, authorization, contact privacy, message validation, contextual responses, persistence, and invitation transitions. Add regression tests for bug fixes.
- Do not weaken or mock away security checks merely to make tests pass.
- Update documentation or add an ADR for significant architectural decisions.

## Checks and reporting

- The application scaffold and its commands do not exist yet. Discover available tooling from the repository, manifests, CI, and documentation; never invent commands.
- Run the relevant tests, lint, type checks, and builds that exist before declaring a task complete.
- Report the exact commands executed and their actual results, including pass and fail counts and relevant errors.
- Explicitly list checks that were not run and why. Never claim tests passed if they were not run or if no suite exists.

## Change hygiene

- Inspect `git status` before editing and preserve existing user changes.
- Avoid unrelated changes and unnecessary dependencies. Prefer existing tools and the standard library, and justify any new dependency.
- Do not commit, push, create branches, or open pull requests unless explicitly asked.
