# Untexted Backend

Minimal FastAPI backend for Untexted. Python 3.13 is required.

## Local setup

From the repository root:

```sh
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The virtual environment is local to `backend/` and is ignored by Git.

## Database configuration

The backend reads the PostgreSQL connection string from `DATABASE_URL`. For a
local process connecting to PostgreSQL on the host:

```sh
export DATABASE_URL="postgresql://<user>:<password>@localhost:5432/<database>"
```

The application converts `postgresql://` and `postgres://` URLs to the
`postgresql+asyncpg://` driver URL internally. The URL provided by
`compose.yaml` can therefore be used without changes.

If `DATABASE_URL` is not set, the application still starts and `/health`
continues to work, but `/ready` returns HTTP 503.

## Database migrations

Alembic manages database schema migrations. The configuration is in
`alembic.ini`, and migration scripts are stored in `alembic/versions/`.

The database URL is not stored in `alembic.ini`. `alembic/env.py` reads
`DATABASE_URL` and converts it to the `postgresql+asyncpg://` driver URL used by
the application. Commands that connect to the database exit with an error if
`DATABASE_URL` is not set.

### Run migrations locally

PostgreSQL must be reachable from the host. The `db` service in `compose.yaml`
does not publish a port, so use the Docker Compose command below unless you run
PostgreSQL separately or provide temporary port forwarding.

With the virtual environment activated and `DATABASE_URL` set:

```sh
cd backend
alembic current
alembic upgrade head
alembic downgrade -1
```

### Run migrations through Docker Compose

The backend image installs Alembic from `requirements.txt`, but the current
Dockerfile does not copy the Alembic configuration into the image. Mount the
backend directory when running a migration container:

```sh
docker compose build backend
docker compose run --rm -v "$PWD/backend:/app" backend alembic upgrade head
docker compose run --rm -v "$PWD/backend:/app" backend alembic current
```

The `backend` service supplies `DATABASE_URL` with the `db` hostname, so the
command connects to the PostgreSQL container without exposing its port.

### Create a migration

With a reachable database and `DATABASE_URL` set:

```sh
cd backend
alembic revision --autogenerate -m "describe the change"
```

`target_metadata` is `Base.metadata` from `app/database.py`. Future models
should inherit from `Base` and be imported by the migration environment so they
register in that metadata before autogenerate runs.

The initial migration creates `schema_migrations_check`, a temporary technical
table used to verify upgrade and downgrade. It is not part of the application
data model and is excluded from autogenerate.

## Run locally

With the virtual environment activated:

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The liveness endpoint does not depend on PostgreSQL:

```sh
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

The readiness endpoint checks the database with `SELECT 1`:

```sh
curl -i http://127.0.0.1:8000/ready
```

It returns HTTP 200 with `{"status":"ok"}` when PostgreSQL is available and
HTTP 503 with `{"status":"unavailable"}` otherwise.

## Run tests

With the virtual environment activated:

```sh
python -m pytest
```

Tests import the FastAPI application directly and do not require a running
server or PostgreSQL. The database session is replaced with a dependency
override in the readiness tests.

## Project structure

```text
backend/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── database.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_readiness.py
├── alembic.ini
├── pytest.ini
├── README.md
└── requirements.txt
```
