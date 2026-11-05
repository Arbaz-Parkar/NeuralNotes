# ADR 007: Store chunk embeddings in pgvector

- **Status:** Accepted for the initial retrieval baseline
- **Date:** 2026-11-05

## Context

The in-memory ingestion pipeline already produces stable, page-aware chunks and normalized embeddings. NeuralNotes needs to persist chunk text and provenance alongside vectors so later retrieval can filter results by workspace and cite exact source locations. The selected baseline model emits 384-dimensional vectors.

## Decision

- Use the `pgvector` Python package with SQLAlchemy's PostgreSQL `VECTOR` type.
- Store each chunk under its workspace and document, retaining stable chunk id, page, character offsets, token count, strategy, section path, and embedding model name.
- Store a non-null 384-dimensional embedding vector for the initial `all-MiniLM-L6-v2` baseline.
- Add an HNSW index with cosine distance and a B-tree index over workspace/document ownership.
- Enable the PostgreSQL vector extension idempotently in the Alembic migration. Leave the extension installed if this table migration is downgraded, since other database objects may use it.
- Keep workspace filtering explicit in future retrieval queries and test cross-workspace isolation.

## Consequences

- Chunk text and provenance can be stored with vectors for later dense retrieval and source citations.
- The fixed 384 dimension matches the current embedding model; changing to a different vector dimension will require a schema migration or a separate embedding table.
- The HNSW index accelerates cosine search, while query code remains responsible for applying the workspace filter.
- The vector schema is PostgreSQL-specific; unit tests inspect metadata, and migration verification uses the local PostgreSQL container.

## Sources

- [pgvector Python package 0.5.1](https://pypi.org/project/pgvector/0.5.1/)
- [pgvector-python SQLAlchemy documentation](https://github.com/pgvector/pgvector-python#sqlalchemy)
