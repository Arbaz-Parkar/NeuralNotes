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
