# Embedding model comparison: MiniLM and BGE

**Date:** 2026-11-15  
**Dataset:** `dpr-pilot-v0.12`  
**Retriever:** hybrid BM25 + dense reciprocal-rank fusion, default RRF constant 60  
**Baseline:** fixed-size workspace, `sentence-transformers/all-MiniLM-L6-v2`  
**Candidate:** fixed-size workspace, `BAAI/bge-small-en-v1.5`  
**Comparison:** paired percentile bootstrap, 2,000 resamples, seed 0, 95% intervals.

Both workspaces contain the same nine papers and 2,145 fixed-size chunks. The BGE model was selected based on the dev comparison before running the held-out test comparison. The test split was used for confirmation only, not tuning.

## Development results

There were 56 paired dev queries. Candidate-minus-baseline differences at `k=10`:

| Metric | Difference | 95% paired interval |
| --- | ---: | ---: |
| MRR | +0.1220 | [+0.0233, +0.2214] |
| nDCG | +0.1045 | [+0.0287, +0.1902] |
| Recall | +0.0804 | [-0.0268, +0.1875] |

MRR and nDCG intervals are above zero on this dev set. Recall's interval crosses zero.

## Held-out test results

There were 18 paired test queries. Candidate-minus-baseline differences at `k=10`:

| Metric | Difference | 95% paired interval |
| --- | ---: | ---: |
| MRR | +0.0316 | [-0.1111, +0.1883] |
| nDCG | +0.0269 | [-0.0662, +0.1310] |
| Recall | +0.0000 | [+0.0000, +0.0000] |

The test point estimates for MRR and nDCG are positive, but both intervals cross zero. Recall is unchanged. The test results therefore do not confirm a performance gain; with 18 queries, they also do not establish that BGE is worse.

## Decision and limits

Keep `sentence-transformers/all-MiniLM-L6-v2` as the default embedding model. Retain BGE as an experimental option: the dev result is promising, but the held-out sample did not confirm it. This comparison measures each model inside the existing hybrid retriever; the evaluation CLI does not currently expose dense-only retrieval. Results are limited to this corpus, chunking strategy, and small query set.
