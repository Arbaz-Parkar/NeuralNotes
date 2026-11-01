# NeuralNotes: Implementation Brief for Codex

NeuralNotes is the student's flagship portfolio project for AI, ML, data science and GenAI internship applications. It is being built over about three weeks (target: working core by 22 November 2026). Read this entire brief before writing any code.

Fill in before sending:
- Start date: [1 November]. Target date: 22 November 2026 (Can Increase until the end of the month). Working hours per day: [2 hours]
- LLM access available: anything that works well and is free
- Cloud: no idea (guide me. something that works well and is free). Managed Postgres preference: no idea (something that works well and is free)
- Hardware: GPU is an RTX 2050 with an i5 11400h and 16gb of ddr4 ram. let me know if that suffice, otherwise switch to cpu only
- If any item is blank, ask me once at the start, then proceed with the safest default.

## 1. Role and working style

Act as a senior AI/ML engineer and mentor. The student wants to become a GenAI/LLM engineer, AI architect or research scientist over the next eight years, and this project is the first step. The student is not buying code. The student is buying understanding, evidence of skill, and a repository that proves it. So:

- Build in the phases of section 8, in order. Finish and verify one phase before the next. Keep the repository runnable at the end of every session.
- Be evaluation-first: build the evaluation harness (Phase 4) before optimizing anything, and justify every retrieval or prompt change with measured results.
- Prefer clear, boring, well-known designs. Add abstractions only where they buy something (swappable providers, testability).
- Library APIs in this field change quickly. Before using any library, check the installed version and read its current official documentation. Do not rely on memory for APIs, model names, or pricing. Pin versions once imports work.
- After each phase, report: files created or changed, what each module does in plain language, tests actually run with real output, commands I must run, and a suggested commit message with the exact `git add` command. Do not commit unless asked.
- Write `docs/phase_notes/phase_N.md` for every phase (one page maximum): what was built, why, trade-offs, pitfalls, and five interview questions with short answers. This is how the student learns what was built.
- Append to `docs/devlog.md` at the end of each session (date, what was done, blockers, next step). On each Sunday add a short weekly review. This mirrors the daily check-in habit employers ask for.
- Give exact Windows PowerShell commands. Investigate root causes of errors instead of retrying random fixes.
- Tell me clearly when I must do something manually (API keys, cloud setup, dataset download).
- Ask a question only when this brief cannot answer it.

## 2. What NeuralNotes is

NeuralNotes is a study and research workspace where every answer is traceable, measured and improvable.

A user uploads papers, lecture notes and documents into a workspace. They ask questions and receive streamed answers with clickable citations to the exact source passages. When a question needs several steps, a research mode plans sub-questions, retrieves evidence, checks whether it is sufficient, and writes a cited report. The knowledge base is also exposed as an MCP server so other AI clients can search it. Behind the interface sit an evaluation harness, tracing and cost tracking, security tests, and a cloud deployment, so quality is a number, not a feeling.

Most "chat with your PDFs" demos stop after retrieval and generation. NeuralNotes is meant to stand out by showing the engineering around them:

- Evaluation: a verified golden dataset, retrieval and generation metrics, judge calibration, confidence intervals, and a regression gate in CI.
- Retrieval engineering: three chunking strategies, hybrid search (BM25 plus dense vectors), fusion, reranking, and query transformation, each measured in ablations, including the ones that did not help.
- Observability: end-to-end traces, token and cost accounting, latency percentiles, versioned prompts.
- Agentic workflows with LangGraph and an MCP server.
- Machine learning that is more than API calls: a scikit-learn query router, embedding analysis and clustering, optional PyTorch fine-tuning.
- Production practice: typed Python, tests, Docker, CI/CD, cloud deployment, security hardening against prompt injection and data leakage.

Audiences: a recruiter or engineer skimming the README (needs a hero demo, architecture diagram, real numbers), an interviewer asking technical questions (needs honest design notes), and the student, who must be able to explain every module.

## 3. What employers ask for, and where NeuralNotes shows it

Derived from entry-level listings the student collected and from current market analyses. Each item maps to a feature so nothing in the project is decoration.

- Python, clean modular testable code, OOP, generators, decorators, comprehensions, iterators, package management, exceptions, file processing: the whole codebase, plus small from-scratch components (section 6.4).
- Data structures and algorithms, complexity analysis: from-scratch BM25 with an inverted index and heap-based top-k, reciprocal rank fusion, ranking metrics, a token-bucket rate limiter, and `docs/complexity_notes.md`.
- LLM APIs, prompt writing, testing and refinement, structured outputs: provider abstraction (Phase 3), versioned prompt files with tests (Phase 6), Pydantic-validated outputs.
- Evaluating AI answers for accuracy, consistency and bias, and recording results: evaluation harness with golden set, consistency (paraphrase) tests, robustness tests, and a recorded experiment log (Phases 4 and 5).
- Preparing, cleaning and labelling data: ingestion cleaning, the verified golden dataset, the labelled query-intent dataset.
- Basic ML with scikit-learn, train/test/overfitting, Pandas and NumPy: query router with cross-validation and learning curves, error analysis in Pandas (Phase 8).
- RAG, vector databases, hybrid search, reranking: Phases 2, 3 and 5. pgvector as the primary store, with a Chroma adapter.
- LangChain and LangGraph, MCP, agents: LangGraph research agent, a LangChain baseline for comparison, and an MCP server (Phases 5 and 7).
- LLM tracing and observability (Langfuse, LangSmith or similar), logs and traces for debugging: Phase 6.
- APIs and production services: FastAPI with async, SSE streaming, OpenAPI, error model, health checks.
- Cloud (GCP: Cloud Run, Cloud Storage, Secret Manager, IAM, BigQuery basics), Docker, CI/CD, SQL, Git, Linux: Phase 10 and the Postgres data model.
- Document and voice workflows (OCR, speech-to-text): optional ingestion adapters in Phase 8.
- Communication: documentation, ADRs, experiment logs, a short technical report, and a demo script.
- Security and responsible AI: Phase 9 and a system card.

## 4. Scope and priorities

P0 (the core that must work by 22 November): Phases 1 to 7, a minimal UI in Phase 9, containerization and one working deployment path in Phase 10, README and docs.

P1 (do if P0 is on schedule): Chroma adapter and parent-child retrieval, LangChain baseline comparison, MLflow tracking, scikit-learn router wired into the pipeline, knowledge map, OCR and audio ingestion, study tools (summaries, flashcards, quizzes with structured output), BEIR sanity check, Cloud Run deployment with CI/CD.

P2 (stretch): embedding or reranker fine-tuning with PyTorch, contextual retrieval enrichment, RAGAS or DeepEval cross-check of the custom judge, semantic cache, Locust load test, BigQuery export of logs, Presidio PII redaction, human-in-the-loop interrupts in the agent.

Non-goals: fine-tuning large language models, billing or complex multi-tenancy, OAuth, Kubernetes, Kafka, mobile apps, scraping the web. Frameworks such as CrewAI, AutoGen and Google ADK are to be read about and compared in an ADR, not built.

Cut rule: if behind schedule, cut P1 and P2 items. Never compromise evaluation, tests, or honest documentation to add features.

## 5. Architecture

Use ports and adapters (hexagonal) so components are swappable and testable:

- Core domain (pure Python, no I/O): document and chunk models, chunkers, BM25, fusion, metrics, prompt rendering, evaluation logic.
- Ports (Protocols): `LLMProvider`, `EmbeddingModel`, `VectorStore`, `Reranker`, `DocumentParser`, `Tracer`, `Cache`.
- Adapters: OpenAI-compatible endpoint (covers OpenAI, Gemini's compatible endpoint if available, and Ollama), a native Gemini adapter, optionally Anthropic; pgvector and Chroma stores; sentence-transformers embeddings and reranker; OpenTelemetry tracer.
- Services: ingestion service, query service, research (agent) service, evaluation service.
- Interfaces: FastAPI REST and SSE API, MCP server, CLI for scripts, React frontend.

Flows:

1. Ingestion: upload, validate, parse, clean, chunk with selected strategy, embed (cached by content hash), store text, metadata and vectors, index for BM25. Runs as a background job with status.
2. Query: classify or route, rewrite if needed, retrieve (dense plus BM25), fuse, rerank, build context under a token budget, generate a cited answer with structured output, verify citations against retrieved chunks, return answer with trace id.
3. Research mode: LangGraph graph (plan, retrieve per sub-question, grade evidence, refine loop with a hard cap, synthesize, verify) with checkpointing.
4. Evaluation: load dataset, run pipeline variants with fixed seeds and cached model calls, compute metrics, compare variants statistically, write a versioned report.

Include a Mermaid component diagram in the README and `docs/architecture.md`.

## 6. Technology stack

Verify current stable versions and APIs from official documentation before using them.

### 6.1 Language, tooling, quality
Python 3.12 (check wheel availability for every dependency; fall back to 3.11 in a fresh venv if needed). `uv` for dependencies if it works smoothly, otherwise `pip` with `pyproject.toml`. ruff for lint and format, mypy or pyright for types, pytest and pytest-cov, pre-commit, a Makefile or justfile with `make test`, `make lint`, `make eval`, `make run`. Type hints and docstrings on public functions. Logging with structured JSON output (structlog or standard logging with a JSON formatter).

### 6.2 Backend
FastAPI with Pydantic v2 (models, validation, settings through pydantic-settings), Uvicorn, async endpoints for network-bound work, Server-Sent Events for streaming, OpenAPI docs, a consistent error format (problem-details style), request IDs, API versioning (`/v1`), pagination, idempotency keys on uploads, rate limiting.

### 6.3 Data and retrieval
- PostgreSQL with pgvector as the primary store for metadata, chunks, vectors, job state, query logs, and evaluation records. HNSW index (cosine) on embeddings, GIN index for full-text, B-tree on workspace and document ids. SQLAlchemy 2.x and Alembic migrations; raw SQL where clearer.
- Chroma adapter for a zero-setup local mode (P1), validated by the same adapter contract tests.
- Embeddings: a small, well-known open embedding model through sentence-transformers as the default (local, free), recorded in config with dimension. An API embedding adapter is optional. Compare two models in an ablation.
- Reranker: a cross-encoder through sentence-transformers on the top 20 to 30 candidates.
- BM25: implemented from scratch (inverted index), validated against a reference library in tests.
- Parsing: evaluate two PDF parsers on five sample papers (two-column layout, equations, tables), then choose and record the decision in an ADR. Note licence implications (for example AGPL for some libraries). Markdown and plain-text parsers are required. OCR and audio are P1.

### 6.4 From-scratch components (small, tested, explained)
These show fundamentals and are used by the project: BM25 with an inverted index and a min-heap for top-k; reciprocal rank fusion; Recall@k, MRR and nDCG; a token-bucket rate limiter; an LRU cache for response caching (optional). Document time and space complexity for each in `docs/complexity_notes.md`. Use libraries everywhere else.

### 6.5 LLM layer
- A thin provider interface with `generate`, `stream` and `generate_structured(schema)`. Low temperature by default, timeouts, retries with exponential backoff and jitter, and a fallback provider.
- Model routing by configuration: a cheaper model for rewriting and judging, a stronger model for final answers (P1).
- Prompts live in versioned files (YAML or Jinja templates) with an id, version, hash, and changelog. The prompt version is attached to every trace and evaluation run. Prompts have unit tests (rendering, required variables, length budget).
- Caching: embeddings keyed by content hash; LLM calls keyed by provider, model, prompt hash and parameters, in a record-and-replay cache used for evaluations so reruns are free and deterministic.
- Cost guard: token counting, per-request and per-day budget limits through environment variables, estimated cost in traces.

### 6.6 Orchestration and agents
Core RAG pipeline in plain Python so the student understands each step. LangGraph for the research agent. A small LangChain-based baseline RAG chain (P1) built only to compare quality, latency and code size against the custom pipeline in the same evaluation harness. The official MCP Python SDK for the MCP server.

### 6.7 Observability and experiment tracking
OpenTelemetry spans around every pipeline stage, exported through OTLP to Langfuse (cloud free tier or self-hosted if light enough) or Arize Phoenix running locally. Check current self-hosting requirements and choose the lightest option that works on a laptop. Do not send private document content to third-party services by default. MLflow local tracking for evaluation runs (P1).

### 6.8 Frontend
React, TypeScript and Vite, with a typed API client generated from the OpenAPI schema. Keep styling simple (Tailwind or plain CSS). Recharts for metric charts, D3 or Plotly only for the knowledge map. The frontend should take no more than about 15 percent of total effort. Fallback: if the frontend does not exist by the end of Phase 8, build the UI in Streamlit instead and say so.

### 6.9 Deployment
Docker (multi-stage, non-root user, healthcheck), Docker Compose for local development (api, postgres with pgvector, tracing backend, frontend), GitHub Actions for CI/CD. Target: GCP Cloud Run for the API, Cloud Storage for uploads, Secret Manager for secrets, Artifact Registry for images, Workload Identity Federation for deployment (no long-lived JSON keys). Postgres through a managed free-tier provider or Cloud SQL, decided with the student because of cost. Set budget alerts and scale-to-zero before enabling anything that bills. Fallback: Render, Fly.io or Hugging Face Spaces.

## 7. Data model (outline)

- workspaces, documents (hash, mime type, source and licence metadata, status), chunks (id, document id, text, position, page, section path, token count, chunk strategy, embedding, text-search vector), jobs (type, status, error), queries (question, answer, citations, latency, tokens, cost, trace id, prompt version; content logging can be disabled), eval_datasets, eval_cases, eval_runs, eval_results, prompt_versions.
- Every table that holds user data has a workspace id. Every query filters by it. Tests must prove one workspace cannot retrieve another's chunks.

## 8. Phases

Dates are targets. Adjust to the real start date but keep the order.

### Phase 1: Foundation and audit (day 1)
Tasks: inspect the workspace, Git state, Python version and any existing NeuralNotes code, then report what exists and wait for my answer before deleting anything. Scaffold the `src/` package, settings, logging, error types, tooling, pre-commit, Makefile, docker-compose with Postgres and pgvector, a health endpoint, and the first CI workflow (lint and tests). Write ADR 001 (architecture style) and a repository `.gitignore` that excludes data, vector stores, `.env`, caches, and generated outputs.
Deliverables: runnable skeleton, passing CI, `docs/adr/`, `.env.example`.
Acceptance: `make test` and `make lint` pass, `docker compose up` starts the database, the health endpoint works.

### Phase 2: Ingestion, chunking, indexing (days 2 to 3)
Tasks:
- Corpus: a script that downloads a fixed set of 30 to 60 open-access ML and NLP papers (and optionally the student's own notes) from official sources using a committed manifest of identifiers. Check each document's licence through the source's metadata. Never commit PDFs. Record source and licence in the database.
- Parsers (PDF, Markdown, text), cleaning (headers, footers, hyphenation, whitespace), metadata extraction (title, page, section path).
- Three chunking strategies behind one interface: fixed-size with overlap by tokens; recursive or structure-aware by headings and paragraphs; semantic or sentence-window with neighbour expansion. Chunk ids are stable and derived from content and position. Property-style tests: no empty chunks, overlap respected, concatenation covers the source.
- Embedding with caching by content hash, batch processing with generators, storage in pgvector, BM25 index build.
- Background ingestion job with status reporting and error capture.
Deliverables: ingestion CLI and API endpoint, chunker tests, ingestion statistics report (documents, chunks per strategy, token distribution).
Acceptance: the corpus ingests end to end for all three strategies, re-running is idempotent, parser comparison ADR written.

### Phase 3: Baseline RAG service (days 4 to 5)
Tasks:
- Dense retrieval over pgvector with workspace filtering.
- Context assembly under a token budget with deduplication and ordering.
- Grounded generation with a structured output (answer, citations by chunk id, optional follow-up questions). Citations are validated: every cited id must be in the retrieved set, otherwise the answer is regenerated once or marked invalid.
- Abstention: if retrieval confidence is low or the model reports insufficient evidence, the system says so.
- LLM provider interface with the OpenAI-compatible adapter, one native adapter, retries, timeouts, caching, and cost guard. An offline mode with a deterministic fake provider for tests.
- API: `POST /v1/documents`, `GET /v1/jobs/{id}`, `POST /v1/query`, `POST /v1/query/stream` (SSE), consistent errors, request ids.
Deliverables: working baseline with documented API, contract tests for adapters, API tests using a mocked provider.
Acceptance: a question about an ingested paper returns a cited, grounded answer; invalid citations are caught in tests.

### Phase 4: Evaluation harness, built before any optimization (days 6 to 7)
Tasks:
- Golden dataset: 80 to 120 questions over the corpus, as JSONL. Types: single-passage factual, multi-hop (two or more passages), comparison, numeric, and unanswerable (at least 15 percent). Process: sample passages, generate candidate questions and reference answers with an LLM, then the student verifies every item by hand and marks it verified. Only verified items count. Evidence is stored as document id plus character span or quoted text, not chunk ids, so labels stay valid when chunking changes (a chunk is relevant if it overlaps the evidence span by a stated threshold). Split into dev (about 70 percent, used for tuning) and test (about 30 percent, never used for tuning).
- A separate adversarial set: documents containing injected instructions, typo and paraphrase variants of questions, and out-of-scope questions.
- Retrieval metrics: Recall@5, 10, 20, MRR@10, nDCG@10, hit rate, computed with the from-scratch implementations and tested on toy examples with known answers.
- Generation metrics: faithfulness (claims supported by the cited evidence, using an LLM judge with a rubric), answer correctness against the reference, citation precision and recall, abstention accuracy and over-abstention rate, consistency across paraphrases, latency p50 and p95, tokens and estimated cost.
- Judge calibration: the student hand-labels 40 to 60 items; report agreement and Cohen's kappa between judge and human; use temperature zero, a versioned judge prompt, and a judge model different from the generator where possible; check for position bias if comparing answers.
- Statistics: bootstrap confidence intervals for every metric; paired bootstrap or permutation tests when comparing two variants; fixed seeds; record environment and versions.
- Runner: `make eval` runs a variant on a split and writes a versioned JSON report plus a Markdown summary, and appends to `docs/experiments/` using a template (hypothesis, setup, results with intervals, decision, next step). Use record-and-replay caching so reruns cost nothing.
- Regression gate: a retrieval-only evaluation on a tiny committed fixture corpus that runs in CI without any LLM calls and fails the build if nDCG@10 drops below a stored threshold.
Deliverables: evaluation harness, golden dataset (without copyrighted text beyond short quoted evidence), baseline report, calibration report, `docs/evaluation.md`.
Acceptance: the Phase 3 baseline has measured numbers with confidence intervals; metric functions pass known-answer tests.

### Phase 5: Retrieval upgrades with ablations (days 8 to 10)
Tasks, each evaluated on the dev split and confirmed once on the test split:
- BM25 from scratch with tuned `k1` and `b`, validated against a reference library.
- Hybrid retrieval with reciprocal rank fusion, with the fusion constant examined.
- Cross-encoder reranking, with the latency trade-off measured.
- Query transformation: conversation-aware rewriting, multi-query expansion. HyDE is P2.
- Chunking comparison across the three strategies; parent-child ("small-to-big") retrieval (P1).
- Two embedding models compared; top-k and context-size sweeps.
- A LangChain baseline chain (P1) evaluated in the same harness.
- Optional BEIR dataset sanity check (for example SciFact) to compare nDCG@10 against published numbers (P1). Verify dataset licence and download instructions from the official source.
Method: change one factor at a time, then combine the best settings. Do not pick settings by looking at test results. Report negative results honestly.
Deliverables: an ablation report in `docs/experiments/`, a chosen default configuration with justification (ADR), and `docs/report/ablation_study.md`, a five to eight page technical report answering: how much do chunking, hybrid retrieval, reranking and query transformation each contribute on a small technical corpus, and at what latency and cost?
Acceptance: the default pipeline measurably beats the Phase 3 baseline on the dev split with a statistically defensible margin, or the report explains why not.

### Phase 6: Observability, prompts, cost and latency (day 11)
Tasks: OpenTelemetry spans for ingest, embed, retrieve, rerank, generate, judge; attributes for model, token counts, latency, estimated cost, prompt version, retrieval scores; trace id returned in API response headers; export to the chosen tracing backend; link evaluation cases to traces; a latency and cost summary (p50, p95, tokens per query); prompt registry with versions and tests; cost guard enforcement; structured logs with request ids and no document content by default.
Deliverables: tracing setup instructions, screenshots from real traces, `docs/observability.md`.
Acceptance: one query produces a complete trace with every stage; the cost guard blocks a request that exceeds a set budget in a test.

### Phase 7: Agentic research mode and MCP server (days 12 to 13)
Tasks:
- LangGraph research graph: plan sub-questions, retrieve per sub-question, grade whether evidence is sufficient, refine with a hard iteration cap, synthesize a cited report, verify citations. Typed state, checkpointing to the database, timeouts, and a clear stop reason. Endpoint `POST /v1/research` streaming step events.
- Tools given to the agent: `search_notes`, `read_passage`. Keep the tool set small and allow-listed.
- MCP server using the official Python SDK exposing `search_notes`, `get_passage`, and `list_documents`, with input validation and workspace scoping. Test with the MCP Inspector and with at least one real MCP client, and document setup.
- Evaluate agent versus single-shot pipeline on the multi-hop subset: correctness, citation quality, latency, tokens, cost. Report honestly even if the agent is not better.
Deliverables: agent and MCP code, step-trace screenshots, comparison report, ADR on agent design.
Acceptance: a multi-hop question produces a cited report with a visible step trace; the MCP server answers search requests from an external client.

### Phase 8: Machine learning and data science layer (days 14 to 15)
Tasks:
- Query router with scikit-learn: build a labelled query dataset (about 200 to 300 queries; categories such as lookup, multi-hop or comparison, summarization, out-of-scope), with the student verifying labels. Baselines: TF-IDF plus logistic regression, then embedding features plus logistic regression. Evaluate with stratified cross-validation, a held-out test set, confusion matrix, learning curve, and a short demonstration of overfitting. Wire the router into the query path (P1) and measure the effect on cost and quality.
- Embedding analysis in a notebook: PCA and UMAP of chunk embeddings coloured by document and by topic; clustering for topic discovery with a human check of cluster labels. This feeds the knowledge map (P1).
- Error analysis in Pandas on evaluation results: failure taxonomy (retrieval miss, ranking error, context overflow, generation unfaithfulness, over-abstention), relationship between retrieval rank and correctness, and a cost versus quality curve. Clean, reproducible notebooks with seeds and a short written narrative.
- P1: OCR for scanned PDFs, and audio transcription with timestamps using a local speech model. Timestamped chunks cite the audio position. Verify tool versions and licences.
- P2: fine-tune a small embedding model or reranker with PyTorch via sentence-transformers on a training split of synthetic query and passage pairs with mined hard negatives, evaluate on held-out data, and guard against leakage between training pairs and the golden set.
Deliverables: router code and report, analysis notebooks, `docs/ml_notes.md` explaining training, testing, overfitting and the choices made.
Acceptance: the router's cross-validated results and test results are reported with intervals and compared with a majority-class baseline.

### Phase 9: Frontend and security hardening (days 16 to 18)
Frontend: library page (upload, ingestion status), chat page with streamed answers, clickable citations opening the source passage with page number, a "why this answer" drawer (retrieved candidates with scores, rerank scores, prompt version, trace link), research page showing agent steps, evaluation page (run history, metric charts with intervals, drill-down to failed cases). Knowledge map (P1). Keep it clear and simple; handle loading, error and empty states.
Security and responsible AI:
- Workspace isolation tests (no cross-workspace retrieval), authentication by API key at minimum, per-key rate limiting (token bucket), upload validation (type sniffing, size and page limits), safe parsing, CORS configuration, secrets only in environment variables, dependency audit (pip-audit and npm audit) in CI.
- Prompt injection: treat retrieved text as data, clear instruction hierarchy in prompts, tool allow-lists, citation requirement, output sanitization (render markdown safely; block remote images and links not in the source list), and an indirect-injection test suite that reports attack success rate before and after mitigations. Map findings to the OWASP Top 10 for LLM Applications in `docs/security.md`.
- Privacy: no document content in logs by default, a setting to disable query logging, optional PII redaction (P2), a visible notice when text is sent to a hosted provider.
- `docs/system_card.md`: intended use, data, models, evaluation results, known failure modes, bias and consistency findings (for example performance across question types and document types), and limitations.
Deliverables: working UI, security tests and report, system card.
Acceptance: security tests pass; the injection suite results are reported with numbers.

### Phase 10: Deployment, CI/CD, documentation and demo (days 19 to 22)
Tasks:
- Dockerfile for the API and frontend, a complete docker-compose for local use, health and readiness endpoints, graceful shutdown, structured logs.
- GitHub Actions: lint, type-check, tests with coverage, dependency audit, image build, the retrieval regression gate, and (P1) deployment to Cloud Run with Workload Identity Federation. Ask me before enabling anything that costs money.
- Deploy the API (and frontend) to the chosen platform with a managed Postgres. Document costs, budget alerts, region choice, and rollback by revision.
- P2: Locust load test with p95 results; BigQuery export of query logs with a few SQL analyses.
- Documentation: README (see section 11), architecture and sequence diagrams, ADRs (at least eight: vector store, orchestration approach, chunking, fusion and reranking, evaluation design, observability, agent design, deployment), runbook, and a demo script.
- A recorded or scripted two-minute demo plan and a screenshot set from real runs.
Deliverables: live URL (or a documented fallback), complete docs, reproducibility instructions.
Acceptance: a fresh clone can follow the README to run locally; CI is green; the demo plan works end to end.

## 9. Evaluation rules (apply across phases)

- Never tune on the test split. Never report a result from a smoke test or a single run as a finding.
- Report every comparison with confidence intervals or an explicit test, and state sample sizes.
- Keep a versioned record for every evaluation run: dataset version, config, prompt versions, model names, seeds, library versions, date.
- State the limits of an LLM judge and of a small corpus plainly in the docs.
- Keep evaluation cheap: replay cache, small judge model, retrieval-only runs in CI.

## 10. Testing and quality gates

- Unit tests: chunkers, parsers, BM25, fusion, metrics (known-answer cases), prompt rendering, schema validation, cost guard, rate limiter.
- Contract tests: every adapter for each port passes the same suite (vector stores, providers, embedders), using fakes where possible so no network or model download is needed.
- API tests with a test client and mocked providers, including error cases and workspace isolation.
- Integration tests (marked and documented) for real models and databases.
- Coverage target about 80 percent on core logic. Ruff, type checks, import checks, and a Docker build must pass.
- Report real test output only.

## 11. Documentation and portfolio deliverables

README: one-paragraph problem statement, hero GIF or screenshots from a real run, the architecture diagram, key measured results (retrieval and generation metrics with intervals, latency, cost per query), a short "what I learned and what did not work" section, quick start, deployment notes, limitations, and references. Present results as short labelled lists and plots, not comparison tables.

Docs: `architecture.md`, `evaluation.md`, `observability.md`, `security.md`, `system_card.md`, `ml_notes.md`, `complexity_notes.md`, `runbook.md`, `adr/`, `experiments/`, `phase_notes/`, `devlog.md`, and the ablation report.

At the end, in the chat only (not in the repository), give the student: four resume bullets using only measured numbers, fifteen likely interview questions with concise answers (including trade-offs between retrieval methods, why an LLM judge needs calibration, how prompt injection was tested, and what the agent did and did not improve), and a two-minute demo script.

## 12. Schedule

- Week 1 (1 to 7 November): Phases 1 to 4.
- Week 2 (8 to 14 November): Phases 5 to 7 and the start of Phase 8.
- Week 3 (15 to 22 November): finish Phase 8, Phases 9 and 10, with two buffer days.
At the end of each week write a weekly review in the devlog with progress against this plan and an honest list of what slips.

## 13. Honesty rules

- Never fabricate metrics, screenshots, citations, test output, licences or dataset statistics.
- Never claim a feature works until it has run. Mark unfinished items as unfinished in the README.
- Label synthetic data, LLM-generated data, and verified data differently.
- Do not copy copyrighted text into the repository beyond short quoted evidence spans.
- If a technique fails to help, report it.
- Keep documentation consistent with the code that exists.

## 14. Definition of done

- A fresh clone runs locally with documented commands.
- Ingestion, hybrid retrieval with reranking, cited streaming answers, research mode, and the MCP server work end to end.
- The evaluation harness, golden dataset, calibration, ablations, and the technical report contain real numbers with confidence intervals.
- Tracing, prompt versioning, and cost accounting work and are demonstrated with real traces.
- Security tests and the injection results are reported.
- CI is green with the retrieval regression gate.
- A deployment (or documented fallback) is live, and the README, system card, ADRs, and experiment log describe what actually exists.
- Phase notes and devlog exist so the student can explain every part.

## 15. First action

Run Phase 1. Report the Python and tooling situation, any existing NeuralNotes code and your keep, simplify or remove list, and which items from the fill-in block you still need from me. Then build the skeleton.