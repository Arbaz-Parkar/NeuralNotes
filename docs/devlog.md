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
- Added tests for a title page followed by sequential proceedings page numbers and for preserving inconsistent numeric lines. Validation is pending.
- Next: run the cleaning tests, Ruff checks, and a corpus sample to verify the page-number rule.
