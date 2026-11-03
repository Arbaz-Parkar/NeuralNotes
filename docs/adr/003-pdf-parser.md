# ADR 003: Use pypdf for initial PDF text extraction

- **Status:** Accepted for the initial ingestion implementation
- **Date:** 2026-11-03

## Context

Phase 2 needs a PDF text parser that can run locally on the project's Python 3.11 setup. We compared pypdf 6.21.4 and pdfplumber 0.11.10 on five papers from the verified corpus, using each parser's default text extraction. We also added a separate pdfplumber `layout=True` configuration for inspection.

## Evidence

In one run over 84 pages, both default parsers returned the same page counts. pypdf extracted 49,567 whitespace-separated words in about 7.82 seconds; pdfplumber extracted 24,659 in about 19.72 seconds. These are single-run measurements from one Windows machine, not a general performance benchmark.

A visual spot-check of the first paper showed readable word spacing in pypdf's output. The default pdfplumber output joined many adjacent words, which likely accounts for part of its lower whitespace-based word count. The remaining papers were not manually scored, and no table- or equation-specific score was recorded. The comparison and its limitations are documented in [the parser comparison notes](../parser_comparison.md).

## Decision

Use pypdf as the initial PDF text extraction adapter. It was faster in this sample, its inspected output preserved word boundaries, it supports Python 3.11, and it uses the BSD-3-Clause license. The `pdfplumber` package remains in the optional `parser-eval` group so the comparison can be reproduced.

This is an initial implementation choice, not a claim that pypdf handles every layout correctly. PDFs encode presentation rather than reliable semantic structure; equations, tables, multi-column reading order, and scanned pages still need explicit handling or later evaluation. The pypdf documentation discusses these limitations and notes that scanned pages need OCR.

## Consequences

- Add pypdf as a pinned runtime dependency and implement the first PDF parser with it.
- Keep extracted text local and ignored; commit neither PDFs nor extracted paper text.
- Preserve page boundaries and source page numbers so citations can be added later.
- Revisit the parser if parser tests show problems with reading order, equations, or tables. Use OCR only as a separate future capability for scanned pages.

## Sources

- [pypdf text extraction guide](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
- [pypdf BSD-3-Clause license](https://github.com/py-pdf/pypdf/blob/main/LICENSE)
- [pdfplumber text and table extraction guide](https://github.com/jsvine/pdfplumber/blob/stable/README.md)
- [pdfplumber MIT license](https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt)
