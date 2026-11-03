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
- Next: compare two PDF parsers on five sample papers, including two-column layouts, equations, and tables.
