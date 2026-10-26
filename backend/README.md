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

## Run locally

With the virtual environment activated:

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify the health endpoint:

```sh
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Run tests

With the virtual environment activated:

```sh
python -m pytest
```

Tests import the FastAPI application directly and do not require a running
server or database.

## Project structure

```text
backend/
├── app/
│   ├── __init__.py
│   └── main.py
├── tests/
│   └── test_health.py
├── pytest.ini
├── README.md
└── requirements.txt
```
