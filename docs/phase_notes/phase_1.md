# Phase 1: Foundation and audit

## What was built

- A `src/` Python package with validated environment settings, JSON logging, and a small application error hierarchy.
- Ruff, pytest with coverage, pre-commit hooks, development commands, and a GitHub Actions workflow.
- A local PostgreSQL 16 database with pgvector 0.8.7. The database port is bound to localhost and its data is kept in a named Docker volume.
- A FastAPI `GET /health` liveness endpoint that returns `{"status": "ok"}`.
- ADR 001 records the ports-and-adapters architecture decision.

## Verification

- `docker compose config` parsed successfully. After Docker Desktop was started, the database became healthy and the extension query returned `0.8.7`.
- The user checked `GET /health`; it returned `ok`.
- [GitHub Actions run 1](https://github.com/Arbaz-Parkar/NeuralNotes/actions/runs/41446345297) passed dependency installation, Ruff lint, Ruff format, and pytest on Python 3.11 and 3.12.

## Trade-offs and pitfalls

- `/health` checks that the API process responds; it does not check database connectivity. Compose separately checks PostgreSQL readiness.
- The local database uses development credentials and listens only on `127.0.0.1`; these settings are not for deployment.
- PostgreSQL initialization SQL runs only when the data directory is first created. Later schema changes belong in migrations.
- `docker compose up -d` can return before PostgreSQL is ready. Use `docker compose up -d --wait db` before running `psql` commands.

## Interview questions

1. **Why ports and adapters?** It keeps core logic independent from replaceable infrastructure such as databases and model providers.
2. **Why use `pydantic-settings`?** It loads configuration from the environment and validates values at startup.
3. **What does `/health` prove?** Only that the API process responds; it does not prove PostgreSQL is available.
4. **Why use pgvector in PostgreSQL?** The project can keep document metadata and vectors in one database while using PostgreSQL's existing operational model.
5. **What does the first CI workflow check?** Lint, formatting, and tests on Python 3.11 and 3.12; it does not yet build or deploy containers.
