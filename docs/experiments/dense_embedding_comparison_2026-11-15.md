# Dense-only embedding comparison: MiniLM and BGE

**Date:** 2026-11-15  
**Dataset:** `dpr-pilot-v0.13`, dev split, 56 paired queries  
**Retriever:** dense vector search, `k=10`  
**Baseline:** fixed-size workspace, `sentence-transformers/all-MiniLM-L6-v2`  
**Candidate:** fixed-size workspace, `BAAI/bge-small-en-v1.5`  
**Comparison:** paired percentile bootstrap, 2,000 resamples, seed 0, 95% intervals.

Both workspaces contain the same nine papers and 2,145 fixed-size chunks. Candidate-minus-baseline results:

| Metric | Difference | 95% paired interval |
| --- | ---: | ---: |
| MRR@10 | +0.0738 | [+0.0119, +0.1317] |
| nDCG@10 | +0.0946 | [+0.0294, +0.1610] |
| Recall@10 | +0.1875 | [+0.0625, +0.3214] |

All three intervals are above zero on this development sample. This is a promising result for BGE in direct dense retrieval on this corpus and chunking configuration.

## Decision and limits

Keep MiniLM as the default pending a clean held-out confirmation for dense-only retrieval. The previously inspected `dpr-pilot-v0.12` test comparison used hybrid retrieval and was inconclusive; it does not directly confirm this dense-only result. Do not use that already-inspected test split to make another selection. Results are specific to this corpus, model setup, and modest query sample.
