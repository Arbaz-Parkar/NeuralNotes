# ADR 006: Workspace and document metadata schema

- **Status:** Accepted
- **Date:** 2026-11-05

## Context

NeuralNotes can now parse, clean, chunk, and embed a document in memory. The next step is to persist document ownership and source metadata before storing chunk content and vectors. ACL Anthology papers also need their license and verification evidence to remain attached to the imported document.

## Decision

- Add a `workspaces` table as the tenant boundary.
- Give documents a workspace-scoped composite primary key and cascade document deletion when a workspace is removed.
- Store a source hash that is unique within a workspace so a later ingestion flow can detect repeat uploads.
- Keep source URLs, title, author, year, and license evidence on the document record.
- Track the document ingestion state as `pending`, `processing`, `ready`, or `failed`.
- Create the tables through an Alembic migration.

Chunk text and vector storage will be introduced separately, after this metadata schema is established.

## Consequences

- A document's identity is scoped to a workspace, allowing different workspaces to import the same source independently.
- The source hash provides an idempotency key for future ingestion work.
- ACL license evidence stays available for attribution and compliance checks.
- Schema updates are versioned and can be applied consistently with Alembic.
