# BM25 pseudo-relevance query expansion

**Date:** 2026-11-16  
**Dataset:** `dpr-pilot-v0.14`, dev split, 56 paired queries  
**Workspace:** fixed-size (`11111111-1111-4111-8111-111111111111`)  
**Baseline:** BM25, `k1=1.5`, `b=0.75`  
**Candidate:** BM25 with rank-weighted top-term pseudo-relevance expansion; 5 feedback chunks and up to 5 added terms  
**Comparison:** paired percentile bootstrap, 2,000 resamples, seed 0, 95% intervals, `k=10`.

| Metric | Candidate minus baseline | 95% paired interval |
| --- | ---: | ---: |
| MRR@10 | -0.0318 | [-0.0896, +0.0221] |
| nDCG@10 | -0.0443 | [-0.1029, +0.0119] |
| Recall@10 | -0.0982 | [-0.1964, +0.0000] |

The point estimates favor baseline BM25 for all three metrics. The intervals include zero, so this small dev comparison does not establish a reliable difference. It provides no evidence to enable pseudo-relevance expansion by default. Keep it as an optional experiment only.

No held-out test run was used to tune this method.
