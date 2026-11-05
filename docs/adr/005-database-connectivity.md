# ADR 005: Use SQLAlchemy with Psycopg 3 for PostgreSQL access

- **Status:** Accepted for the initial database connection layer
- **Date:** 2026-11-05

## Context

NeuralNotes has a local PostgreSQL 16 database with pgvector enabled, but the application does not yet connect to it. The ingestion pipeline needs a configured and testable database connection before schema and persistence work begins. Development runs on Windows with Python 3.11.

## Decision

Use SQLAlchemy 2.1.8 with Psycopg 3.3.8 and its binary extra. Use the explicit `postgresql+psycopg://` URL scheme. Read the URL from `NEURALNOTES_DATABASE_URL`, defaulting to the local Compose credentials. Create engines through a small factory with `pool_pre_ping=True`; run a `SELECT 1` connectivity check through an explicit connection.

## Consequences

- Engine creation is lazy: the database is contacted only when a connection is requested. This keeps import and engine construction separate from database availability.
- Psycopg's binary extra includes the client libraries needed on the supported Windows development setup, without a local compiler or PostgreSQL client installation.
- The current helper is synchronous and has no table definitions, migrations, sessions, or persistence. If database I/O is later called from async API handlers, that work must use an async engine or a worker thread.
- Keep the local development URL in `.env` and out of logs. The example URL's credentials must match the `POSTGRES_*` Compose settings.

## Sources

- [SQLAlchemy 2.1 engine configuration](https://docs.sqlalchemy.org/en/21/core/engines.html)
- [SQLAlchemy PostgreSQL and Psycopg dialect](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html#psycopg)
- [Psycopg 3 installation guide](https://www.psycopg.org/psycopg3/docs/basic/install.html)
- [SQLAlchemy 2.1.8 release](https://pypi.org/project/SQLAlchemy/2.1.8/)
- [Psycopg 3.3.8 release](https://pypi.org/project/psycopg/3.3.8/)
