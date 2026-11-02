# ADR 002: Use the ACL Anthology for the initial corpus

- **Status:** Accepted
- **Date:** 2026-11-02

## Context

Phase 2 needs a fixed corpus of technical papers with stable identifiers, direct source links, and documented reuse terms. “Open access” alone does not establish permission to store and process a paper. The arXiv API terms distinguish CC0 metadata from paper content, whose redistribution depends on the paper's license; its documented Atom response fields do not include a per-paper license. The ACL Anthology provides stable paper IDs, paper metadata, and direct PDF links. Its current copyright page says materials published from 2016 onward are under CC BY 4.0.

## Decision

Use the ACL Anthology as the source for the initial NLP and language-model paper corpus. Select ACL materials published in or after 2016, and verify each selected paper against its official ACL Anthology landing page before adding it to the manifest. Record the Anthology ID, title, publication year, landing-page URL, PDF URL, license identifier, and license evidence URL. Exclude any paper whose applicable license cannot be established from an official source.

Commit the manifest, not downloaded papers or full abstracts. Download PDFs into ignored local data storage. The downloader must preserve attribution and stay within the source's published access rules.

## Consequences

- The initial corpus will emphasize computational linguistics, retrieval, language models, and evaluation rather than broad machine learning.
- The post-2016 ACL license policy makes the corpus easier to audit, but individual records still need checking because the Anthology hosts materials from other rights holders.
- Papers from arXiv or other sources can be added later only after their content licenses and access terms are checked separately.

## Sources

- [ACL Anthology FAQ: data and direct paper links](https://aclanthology.org/faq/)
- [ACL Anthology copyright and licensing information](https://aclanthology.org/info/contrib/)
- [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html)
- [arXiv API terms of use](https://info.arxiv.org/help/api/tou.html)
