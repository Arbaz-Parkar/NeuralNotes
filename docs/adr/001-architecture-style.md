# ADR 001: Use ports and adapters

- **Status:** Accepted
- **Date:** 2026-11-01

## Context

NeuralNotes needs to work with different language model providers, embedding models, vector stores, document parsers, and tracing backends. The retrieval and evaluation logic should also be testable without network access or a running database. Keeping these concerns mixed together would make provider changes and debugging harder.

## Decision

Organize the application using ports and adapters (also called hexagonal architecture):

- Keep core domain logic, such as chunking, ranking, citation checks, and metrics, independent of I/O.
- Define small Python protocols for external capabilities such as language models, embeddings, vector storage, parsing, and tracing.
- Put vendor-specific integrations behind adapters that implement those protocols.
- Let application services coordinate the core logic and adapters. Keep API, CLI, and MCP interfaces at the boundary.

Dependencies point inward: core logic does not import FastAPI, database clients, or provider SDKs. Start with the smallest interfaces needed by a real use case; add abstractions only when they make a component replaceable or easier to test.

## Consequences

- Core behavior can be tested with deterministic fakes and without credentials or services.
- Adapter implementations can be swapped and checked against shared contract tests.
- There will be some interface and adapter code, so protocols must stay small and useful.
- This structure does not by itself guarantee workspace isolation or security; those still need explicit checks and tests.
