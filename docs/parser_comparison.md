# PDF parser comparison

**Status:** comparison prepared; local extraction and manual review are pending.

## Candidates

- **pypdf 6.21.4** — pure-Python PDF library under BSD-3-Clause. We will use its default `PageObject.extract_text()` mode.
- **pdfplumber 0.11.10** — exposes character geometry and table-extraction tools under MIT. We will compare its default `Page.extract_text()` mode with `Page.extract_text(layout=True)`.

Both libraries support Python 3.11. These are pinned in the `parser-eval` optional dependency group for a reproducible comparison. `pdfplumber` documents layout-preserving extraction as experimental; it is included as a separate configuration so its result can be compared with the default. No OCR is included.

The libraries offer different trade-offs: pypdf is a pure-Python dependency with text and PDF object access; pdfplumber builds on pdfminer.six and also exposes positioned characters, layout tools, and table extraction. The comparison focuses on extracted text and reading order; a later ingestion implementation can use pdfplumber's table tools if the sample shows a practical benefit.

## Sample

The runner uses five papers already present in the verified manifest:

- `2020.emnlp-main.550` — Dense Passage Retrieval for Open-Domain Question Answering
- `2024.emnlp-main.845` — Dense X Retrieval: What Retrieval Granularity Should We Use?
- `2024.eacl-demo.16` — RAGAs: Automated Evaluation of Retrieval Augmented Generation
- `2024.findings-acl.372` — Benchmarking Retrieval-Augmented Generation for Medicine
- `2025.findings-acl.624` — GeAR: Graph-enhanced Agent for Retrieval-augmented Generation

The sample spans different years and paper types. During review, confirm that the five PDFs collectively include two-column pages, equations, and tables; if not, replace a sample with another paper from the manifest and record the reason.

## Method

Run both parsers with default text extraction settings on the same local PDFs. Record the package versions, extraction time, page and word counts, empty pages, replacement characters, and unexpected control characters. These counts help spot extraction failures; they are not a quality score.

Inspect the locally saved text outputs and score each parser from 1 (poor) to 5 (good) for:

- reading order across two columns;
- equation readability;
- table values and reading order;
- section and paragraph flow.

The review sheet also has a notes field for concrete examples. Do not commit extracted text or PDFs. Record scores, observations, and the parser choice here after the comparison has actually run.

## First extraction pass — 2026-11-03

The runner completed on all five papers with both parsers. This was one run on the developer's Windows machine; the timing and counts below are preliminary and are not quality scores.

- **pypdf:** 49,567 extracted words across 84 pages in about 7.82 seconds.
- **pdfplumber:** 24,659 extracted words across the same 84 pages in about 19.72 seconds.
- Both parsers returned the same page count for each paper. The large word-count difference needs inspection in the saved text outputs before it can be explained.

The initial implementation will use pypdf, as recorded in [ADR 003](adr/003-pdf-parser.md). This is a limited decision based on one visual spot-check and single-run counts/timings; human scores for all five papers, equations, and tables are still pending.

A visual spot-check of the first sample showed readable word spacing in pypdf's output and many joined words in pdfplumber's default output. This may explain much of the word-count gap because the current word metric splits on whitespace. The runner also includes pdfplumber's `layout=True` mode as a separate configuration; its result is retained for future comparison but was not used as the basis for this initial choice.

## Run

From the repository root in PowerShell, install the comparison extra and run the tool:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,parser-eval]"
.\.venv\Scripts\python.exe -m neuralnotes.parser_comparison
```

The command writes `summary.json`, `manual_review.csv`, and parser text outputs under the ignored `data/processed/parser_comparison/` directory. Review the text files, complete the CSV scores, then update this document with the real findings and decision.

## References

- [pypdf text extraction guide](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
- [pypdf BSD-3-Clause license](https://github.com/py-pdf/pypdf/blob/main/LICENSE)
- [pdfplumber text and table extraction guide](https://github.com/jsvine/pdfplumber/blob/stable/README.md)
- [pdfplumber MIT license](https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt)
