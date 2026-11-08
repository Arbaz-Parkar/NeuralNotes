# Development log

## Weekly review — 2026-11-01

- Started Phase 1 and confirmed the repository needed its application foundation.
- Phase 1 extended into Day 2; the Week 1 target of completing Phases 1–4 by 7 November remains ahead.
- Next: finish the foundation and verify its database, API, and CI pieces.

## 2026-11-02

- Completed Phase 1: local pgvector database, FastAPI health endpoint, and first CI workflow, alongside the package, settings, logging, errors, and quality tooling.
- Verified the database health and pgvector version (`0.8.7`), the health endpoint (`ok`), and CI on Python 3.11 and 3.12.
- Phase 2 decision: use post-2016 ACL Anthology papers for the initial NLP-focused corpus, with an official license check for every manifest entry.
- Blocker: Docker Desktop was initially stopped; started it and completed the database check.
- Expanded the manifest to fifteen paper records, each checked against its official ACL Anthology license statement; no PDFs are committed.
- Next: extend the manifest toward the 30–60 paper corpus, then implement a rate-conscious downloader.

## 2026-11-03

- Added five more license-checked ACL Anthology papers covering active retrieval, RAG best practices, source reliability, RAG reasoning, and robustness; the manifest now contains twenty records and no PDFs.
- Added five additional license-checked papers on long-context comparison, medical RAG, query robustness, scenario-specific evaluation, and faithfulness; the manifest now contains twenty-five records, with no PDFs committed.
- Added five papers on answer attribution, sentence-level citations, citation quality, outdated knowledge, and evidence-based generation; the manifest now reaches the 30-paper minimum, and no PDFs are committed.
- Implemented a CLI downloader that validates manifest licensing and ACL URLs, saves PDFs to ignored local storage, and streams each file safely with request spacing.
- Downloaded all 30 manifest papers locally: 30 downloaded, zero skipped, zero failed; PDFs remain in Git-ignored storage.
- Started the main README with the verified project status, architecture diagram, Windows quick start, and explicit unfinished work; it will be updated as each phase advances.
- Ran the pypdf versus pdfplumber comparison on five papers (84 pages): pypdf extracted 49,567 words in about 7.82 seconds; pdfplumber extracted 24,659 words in about 19.72 seconds. These one-run counts and timings do not determine quality; manual review is pending.
- A screenshot review of the first paper shows pypdf's spacing is readable while pdfplumber's default output joins many words. Added a `pdfplumber` layout-mode variant to distinguish configuration from parser choice.
- Selected pypdf for the initial PDF parser and recorded the limited evidence and trade-offs in ADR 003. The layout-mode result and human review of all five papers remain open follow-up evidence.
- Added the `DocumentParser` protocol, immutable parsed-document/page types, and a pypdf adapter that preserves one-based page numbers and basic title/author metadata.
- Verified the adapter on `2020.emnlp-main.550`: title extracted, 13 pages, 56,093 characters.
- Added the first pure cleaning pass for line endings, horizontal whitespace, and repeated blank lines; page boundaries, line breaks, and hyphenation are preserved.
- Verified the cleaner: 3 unit tests passed, Ruff lint and format passed, and the sample paper remained 13 pages and 56,093 characters after cleaning.
- Added a local audit command that reports repeated top and bottom page lines to an ignored CSV; it does not remove text. Added unit cases for repeated page numbers and margin-line options.
- Ran the cleaning tests: 5 passed. The corpus audit completed and wrote 113 candidate rows to the ignored CSV; manual classification is still needed before any removal rule is considered.
- pypdf printed a fontTools advisory while processing a CFF Type1 font; the audit completed, and no encoding problem has been confirmed.
- Next: review the candidates before implementing any header/footer removal.

## 2026-11-04

- Updated the README with the verified test and audit results: 5 cleaning tests passed and the corpus run produced 113 candidate rows.
- Fixed the Ruff formatting findings in the cleaning module and its tests; lint and format checks still need to be rerun.
- Reviewed the highest-frequency rows and confirmed the first report grouped sequential printed page numbers (47578 onward) as one repeated numeric line.
- Updated the audit to skip numeric-only margin lines and added a regression test; sequential page-number cleanup remains separate.
- Verified the update: 6 cleaning tests passed, Ruff lint and format checks passed, and the corpus audit wrote 81 candidates, down from 113 in the first run.
- The pypdf fontTools advisory appeared again during the audit; processing completed and no text encoding problem has been confirmed.
- Inspected pages 21–25 of the source-reliability paper. The repeated top lines are multi-page table headings and the bottom captions are table content, so they must be preserved.
- Added a conservative cleanup rule for numeric-only final lines: remove them only when their values follow one consistent sequence across at least 80% of pages and at least three pages.
- Added tests for a title page followed by sequential proceedings page numbers and for preserving inconsistent numeric lines. All 8 cleaning tests and both Ruff checks passed.
- Checked pages 1–3 and 35–36 of the 36-page paper: printed page numbers were removed while the last lines of article text remained.
- Committed and pushed the cleanup as `3c86d4b` (`feat: remove verified sequential page footers`).
- Added a standard-library plain-text adapter that decodes UTF-8 and treats each file as one source page while preserving line endings; its focused tests and validation are pending.
- Added a Markdown parser that preserves the source text as one page and extracts the first level-one heading outside fenced code blocks as the title. Focused tests and validation are pending.
- Added cleanup for explicit soft hyphens: a soft hyphen before a line break is removed along with the break, while hard hyphens remain unchanged. A focused test is pending.
- Scanned the 30-paper corpus for hard-hyphen line breaks and found 8,469 occurrences. The sample contains both true word wraps and valid compounds, so no blanket hard-hyphen removal rule was selected.
- Checked dictionary-based options: wordfreq's frequency data is a snapshot through about 2021, while Pyphen bundles dictionaries under multiple licenses. No new lexical dependency was added.
- Added an immutable `Chunk` model with stable content-and-position ids, source offsets, page number, token count, strategy, and optional section path.
- Added a fixed-size chunker with configurable overlap, page-local token spans, and stable ids. It accepts an injected offset tokenizer so token counts can match the selected model later; no production tokenizer is wired yet.
- Ran 36 unit tests across chunk models, chunking, cleaning, and parser adapters; all passed. Ruff found one import-order issue and two formatting differences. The fixes are applied; Ruff and format checks must be rerun.
- Next: rerun Ruff and format, then select the production tokenizer with the embedding model.
- Selected `sentence-transformers/all-MiniLM-L6-v2` as the first local English embedding baseline and pinned `sentence-transformers==6.2.0` in a separate optional dependency extra. This is an initial baseline, not a measured winner.
- Set the fixed-size chunker's provisional defaults to 100 tokens with 20-token overlap, and added a test for those defaults. The size is chosen to leave headroom under the model's 128-token training sequence; tuning belongs in the later evaluation phase.
- Added ADR 004 and README setup instructions for the optional embedding dependency. The model tokenizer and embedding adapter are not implemented yet; CPU/GPU availability still needs to be checked in the user's Windows environment.
- Next: install the optional extra if needed, confirm the package version and CUDA availability, then validate a real tokenizer call.
- Added `HuggingFaceOffsetTokenizer`, which lazily loads the selected model's fast tokenizer and returns checked character spans without adding special tokens or truncating input. Its unit tests use a fake tokenizer and do not download model files; all 10 passed.
- Ran 18 focused tokenizer and chunker tests; all passed. The real tokenizer loaded with Sentence Transformers 6.2.0 and returned character spans.
- The Windows environment reported `torch.cuda.is_available() == False`, so the tokenizer check used CPU. GPU acceleration is not required for the adapter, and the embedding implementation can use CPU for now.
- Ruff found two line-length issues in the adapter. The fixes are applied; lint and format checks need to be rerun.
- Next: rerun Ruff and format, then implement the sentence-transformer embedding adapter.
- Added an `EmbeddingModel` protocol and a lazy Sentence Transformers adapter for document batches and query vectors. It returns normalized vectors and checks their count, dimension, finite values, and unit length. Fake-model unit tests are in place; focused validation is pending.
- Next: run the embedding adapter tests and Ruff, then make a real model call on a few sample texts before starting database storage.
- Verified the real adapter on CPU: one document vector and one query vector each had 384 dimensions and a norm of 1.0. Sentence Transformers emitted a deprecation warning for the prior dimension accessor; updated the adapter to the documented `get_embedding_dimension()` method.
- The 14 embedding adapter tests passed. Ruff found one line-length/format issue; the fix is applied and lint/format checks need a rerun.

## 2026-11-05

- Added a `Chunker` protocol so ingestion can depend on the chunking interface rather than a specific strategy.
- Added `DocumentIngestionPipeline.prepare`, an in-memory path that parses one source file, applies the existing cleaner, generates page-aware chunks, embeds the chunk texts, and returns metadata with each chunk/vector pair.
- The preparation result is deliberately not persisted yet; a focused fake-adapter test suite is pending before connecting this path to PostgreSQL.
- Next: run the pipeline tests and Ruff, then exercise the pipeline on one local paper before designing database persistence.
- Added the database URL to environment-backed settings and `.env.example`, with SQLAlchemy 2.1.8 and Psycopg 3.3.8 as runtime dependencies.
- Added a lazy SQLAlchemy engine factory and a `SELECT 1` connectivity helper. SQLite unit coverage uses an in-memory database; the local Docker PostgreSQL connection check is pending.
- Next: install the database dependencies, run settings/database tests and Ruff, and verify the connection against the local pgvector container.
- Added SQLAlchemy `Workspace` and `Document` models with workspace-scoped keys, source hashes, and the ACL license evidence fields.
- Added Alembic 1.20.1 configuration and the initial migration for the workspace and document tables. Migration execution against the local PostgreSQL container is pending.
- Added `Chunk` persistence with workspace/document ownership, source offsets, page and strategy metadata, and a 384-dimensional pgvector embedding.
- Added the pinned `pgvector` 0.5.1 Python adapter dependency and an Alembic migration that enables the vector extension and creates a cosine HNSW index. The database migration has not yet been run locally.
- Recorded the vector storage decision and the fixed model dimension in ADR 007; updated the README status and architecture references.
- Validation found a SQLAlchemy helper name collision in the model class, then exposed one remaining old helper reference in the document status default and an import-order issue. The migration stopped before the chunk migration, leaving the already-created workspace and document tables intact. Updated both server defaults to use the explicit `sql_text` alias and followed Ruff's import layout.
- Next: rerun the model tests and Ruff, apply the chunk migration locally, and inspect the chunk table and cosine HNSW index.
- Added a reusable SQLAlchemy session factory and a persistence adapter that hashes source files, saves document/license metadata with embedded chunks, validates vector dimensions, and replaces chunks on repeated imports within the caller's transaction.
- Added SQLite-backed tests for document/chunk persistence, repeat-import behavior, embedding dimension checks, and transactional sessions. Focused validation is pending.
- Next: run the database and ingestion persistence tests with Ruff, then verify a prepared local paper can be written to PostgreSQL.

## 2026-11-06

- Added a one-paper ingestion command that looks up an ACL ID in the verified manifest, processes its local PDF with the selected parser, tokenizer, chunker, and embedder, creates a default workspace when needed, and persists metadata and vectors in a single transaction.
- Added CLI tests for persistence metadata, workspace creation, missing manifest IDs, missing local PDFs, and command failure reporting. The focused CLI, persistence, pipeline, and database tests passed: 12 total.
- Updated the README with the command, local prerequisites, default workspace behavior, and the remaining Phase 2 work.
- Applied the Alembic migrations and ingested `2020.emnlp-main.550` into the default local workspace. PostgreSQL reported the document as `ready` with 181 chunks across 13 pages.
- Ruff found one unused `func` import in the CLI test file. Removed it; rerun lint and formatting checks before committing.
- Sentence Transformers logged that CPU was selected. The 1,026-token warning came from tokenizing a full PDF page to compute character offsets; the pipeline embeds bounded chunks instead.
- Reran the single-paper CLI step's remaining Ruff check after removing the unused import and committed it; local PostgreSQL contains the verified 13-page, 181-chunk result.
- Added a recursive chunker that prefers paragraph, line, sentence, and whitespace boundaries while keeping token limits, overlap, page provenance, and stable ids.
- Added focused tests for structural boundaries, token-limit fallback, overlap, page separation, deterministic ids, and option validation. All 25 focused tests passed and Ruff lint passed.
- Ruff format check identified one test line to reformat. Applied the fix, reran formatting checks successfully, and committed the chunker as `6a92486` (`feat: add paragraph-aware recursive chunking`).
- Added `SentenceWindowChunker` to form sentence-centered chunks with neighboring sentence context, a token cap, and a deterministic punctuation-based boundary heuristic.
- Added tests for neighbor expansion, token limits, long-sentence splitting, common abbreviations, page boundaries, stable ids, and invalid options. The focused tests and Ruff checks passed, and the change was committed as `b85129d` (`feat: add sentence-window chunking`).
- Added a SQLite embedding cache keyed by model name, embedding role, and SHA-256 of input text. Document and query embeddings use separate keys so model-specific encoding routes are not mixed.
- Wrapped the CLI's sentence-transformer adapter with the cache. Cache files are written under the existing Git-ignored `data/cache/` directory; raw text is not stored.
- Added tests for duplicate inputs, order preservation, cross-process reuse, model separation, document/query separation, and corrupt entries. The cache change was committed as `90198cf` (`feat: cache embeddings by content hash`).
- Added batch manifest ingestion with a single reused parser/embedding pipeline, cache, and database engine. Papers are processed sequentially and committed separately; a failed paper is reported without rolling back earlier imports.
- Extended the CLI to accept repeated `--paper-id` arguments or `--all`, and documented the batch workflow.
- Added tests for ordered multi-paper ingestion, continued processing after a missing PDF, per-document database results, invalid selections, and batch failure exit codes. The first test run exposed identical fixture bytes for distinct papers; after correcting that fixture, all 19 focused tests passed, Ruff lint passed, and all 60 files passed the format check.
- The first batch test run exposed a fixture issue: two sample PDFs had identical bytes, so the intended workspace duplicate-source guard rejected the second import. Updated the fixture to use distinct bytes and applied Ruff's import/format fixes.
- Smoke-tested two manifest papers against local PostgreSQL: 2020.emnlp-main.550 was stored as 13 pages and 181 chunks; 2024.emnlp-main.845 as 19 pages and 243 chunks. The batch completed with 2 successes, 0 failures, and 424 chunks.
- Sentence Transformers selected CPU. Its 1,026-token warning came from offset-tokenizing a complete page; the embedding pipeline processed bounded chunks and completed successfully.
- Next: commit batch manifest ingestion, then begin the BM25 retrieval index.

## 2026-11-07

- Confirmed batch manifest ingestion was committed as `3be62d5` and pushed.
- Added an in-memory BM25 index over source-aware chunks. It builds term-frequency postings, applies the BM25 length and inverse-document-frequency formula, and uses a min-heap for deterministic top-k results.
- Added focused unit tests for the scoring formula, case-insensitive tokenization, tie ordering, top-k limits, and invalid input. All 14 focused tests passed; after removing one unused import and applying Ruff's formatting suggestions, committed as `978e2f0` (`feat: add in-memory BM25 retrieval index`).
- Added `docs/complexity_notes.md` with the BM25 formula, complexity estimates, limitations, and the workspace-scoping requirement.
- Added a SQLAlchemy adapter that loads chunks using a workspace-id filter and builds a deterministic in-memory BM25 snapshot. Added SQLite tests for workspace isolation and an empty workspace; validation is pending.
- The combined BM25 and database-adapter test run passed all 16 tests, and all 62 files passed the format check. Ruff found an import-order issue in the adapter test; applied Ruff's suggested import layout, with lint rerun pending.
- Committed and pushed the workspace-scoped BM25 adapter as `3ae63a6` (`feat: build workspace-scoped BM25 indexes`).
- Added `POST /v1/search`, a retrieval-only endpoint that validates query length and top-k bounds, opens a request-scoped database session, filters chunks by workspace, and returns source passages with page/character provenance and BM25 scores.
- Added API tests for workspace isolation and blank-query validation. The focused API, adapter, and BM25 suite passed all 19 tests. Ruff found one import-order issue and one formatter suggestion; both fixes are applied, with lint and format reruns pending.
- Committed and pushed the search API as `d1633b8` (`feat: add workspace-scoped BM25 search API`).
- Expanded the ingestion CLI to select fixed-size, recursive, or sentence-window chunking for both single-paper and batch runs. Fixed-size remains the default; comparative runs should use separate workspace ids so later imports do not replace earlier strategy results.
- Added a workspace-scoped ingestion statistics command that reports ready documents, chunk counts by strategy, and the token-count distribution. It can print Markdown or write a report file.
- Added strategy-selection and statistics tests. The focused ingestion, batch, and statistics suites passed all 14 tests.
- Smoke-tested the 13-page DPR paper in separate workspaces: 195 recursive chunks and 471 sentence-window chunks. The existing fixed-size workspace contains 181 chunks. Generated one Markdown statistics report for each strategy workspace.
- Ruff found an import-order issue in `test_ingestion_cli.py` and one formatting change in `stats.py`; both fixes are applied, with Ruff reruns pending.
- Next: rerun Ruff checks, commit the selectable chunking and statistics milestone, then smoke-test the BM25 search API against the local workspaces.

## 2026-11-08

- Confirmed the selectable chunking and statistics milestone was committed as `6e0e7b2`.
- Followed the project phase order: started Phase 4 retrieval evaluation foundations before treating chunking or search smoke checks as comparisons.
- Added pure functions for Precision@k, Recall@k, HitRate@k, ReciprocalRank@k, and binary nDCG@k, plus known-answer tests. All 12 focused tests and Ruff checks passed; committed as `13ef3ad` (`feat: add retrieval ranking metrics`). No retrieval-quality results are reported.
- Added `docs/evaluation.md` to define metric behavior and document what the benchmark harness still needs, including verified span-based relevance labels, split discipline, aggregation, and uncertainty intervals.
- Added a Pydantic JSONL case schema with explicit answerability, category, dev/test split, reference answer, page-local character evidence spans, and a verification flag. The loader rejects malformed/duplicate ids and returns only verified cases from the selected split.
- Added document/page/span-to-chunk relevance mapping and a callback-based evaluator that reports per-query and macro-averaged ranking metrics at configurable cutoffs. Unanswerable cases are counted separately and excluded from ranking averages; missing chunk matches for verified answerable labels fail loudly.
- Added tests for case validation and loading, evidence overlap, split guards, and metric aggregation. All 21 evaluator and metrics tests passed; Ruff fixes were applied and committed in `1b8c4a5` (`feat: add evidence-based retrieval evaluator`).
- Updated the evaluation notes and README to clarify that the JSON example is unverified, generated chunk counts are smoke observations, and a verified golden set or quality findings do not exist yet.
- Added a scoped database loader for source-aware workspace chunks and refactored the BM25 adapter to use it.
- Added a BM25 evaluation CLI that selects one verified dataset split and one workspace, then writes a timestamped JSON run record and Markdown summary with configuration, aggregate metrics, and per-query values.
- Added CLI/report tests and database loader coverage. All 29 focused tests passed and formatting passed; after fixing the final import-order finding, lint passed and the milestone was committed as `871e17e` (`feat: add versioned BM25 evaluation reports`).
- Documented the PowerShell command and made the absent manually verified dataset explicit; there is still no benchmark result to report.
- Week 1 review (1–7 November): completed the foundation, paper corpus, parsing/cleaning, chunking, embeddings, persistence, ingestion CLI, initial BM25 core and API, and chunking statistics. Phase 4 is behind its original schedule: basic ranking metrics and a BM25 evaluator now exist, but there are no verified golden questions, uncertainty intervals, baseline report, or CI regression fixture. Week 2 will finish the evaluation harness before Phase 5 comparisons; scope should stay focused on the P0 path.
- Added a local source-page inspector that uses the manifest, pypdf parser, and cleaner, and displays page-local character offsets in the same coordinate system as stored chunks. Extracted text is printed to the terminal only.
- Added tests for line ranges and empty pages, plus a labeling guide covering evidence verification, question categories, answerability, and dev/test split discipline. Validation is pending.
- Visually checked the DPR paper's first page against the inspector output. Added one verified development question with a paraphrased answer and a page-local evidence span; the row contains no copied source passage.
- Added a regression test that loads the committed pilot case and checks its verified flag and source span. Validation is pending.
- Added four first-page candidate questions covering sparse baselines, a numeric retrieval result, the two-stage QA framework, and a SQuAD score example. They are kept in a separate JSONL file with `verified: false`, and a test checks that the scoring loader excludes them.
- Next: review the four candidates against the PDF, move only accurate records into the verified dataset, and keep the one-case sample labeled as a pilot. Do not report retrieval quality from it.
- Added a local source-page inspector that uses the manifest, pypdf parser, and cleaner, and displays page-local character offsets in the same coordinate system as stored chunks. Extracted text is printed to the terminal only.
- Added tests for line ranges and empty pages, plus a labeling guide covering evidence verification, question categories, answerability, and dev/test split discipline. Validation is pending.
- Next: run the inspector tests and Ruff, then manually verify the first candidate question and evidence span from the DPR paper before adding a verified dataset record.
