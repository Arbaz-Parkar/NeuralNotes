# Retrieval ablation report: chunking, hybrid fusion, and reranking

**Status:** partial Phase 5 report  
**Dataset:** `dpr-pilot-v0.10`  
**Evaluation date:** 15 November 2026  
**Retrieval metrics:** macro averages over verified answerable queries; 95% paired percentile bootstrap intervals use 2,000 resamples and seed 0.

## Summary

The development results show a consistent ranking improvement when a cross-encoder reranks BM25's top 30 candidates. At k=10, MRR, nDCG, and recall improved for fixed-size, recursive, and sentence-window chunks, and every paired interval for those gains was above zero. The trade-off was substantial: warm-model median retrieval latency rose from 4–9 ms to 477–510 ms.

BM25 plus dense reciprocal rank fusion (RRF) performed worse than BM25 alone before reranking. After reranking, hybrid retrieval did not show a reliable advantage over reranked BM25: fixed-size differences were small and uncertain, recursive results favored BM25, and sentence-window intervals included zero. Hybrid retrieval also added latency.

The held-out comparison of fixed-size BM25 with and without reranking did not confirm a gain. Its k=10 MRR and nDCG differences were slightly negative, with intervals spanning zero. With only 18 answerable test queries, this is inconclusive. The recommendation is to keep BM25 as the default and leave cross-encoder reranking as an optional experiment. Do not promote it as a quality improvement based on this test sample.

## Evaluation setup

The dataset version contains 56 verified answerable development questions and 18 verified answerable test questions. Unanswerable questions are excluded from ranking averages. The same questions and evidence spans were used across each paired run. Evidence-to-chunk relevance used a 0.5 overlap threshold.

BM25 used `k1=1.5` and `b=0.75`. Hybrid retrieval fused the BM25 and dense top-candidate rankings with RRF constant 60. The cross-encoder reranked 30 candidates using `cross-encoder/ms-marco-MiniLM-L6-v2`. The configured embedding model was the stored workspace model, `sentence-transformers/all-MiniLM-L6-v2`.

Reported latency is warm-model per-query retrieval latency. It includes query embedding when used and cross-encoder scoring when enabled; model loading and warm-up are excluded. Runs used the same local CPU environment. These measurements describe this machine and corpus, not a production service.

## Development results at k=10

| Chunk strategy | Method | MRR | nDCG | Recall | p50 latency | p95 latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Fixed-size | BM25 | 0.4363 | 0.4806 | 0.6875 | 4.04 ms | 5.54 ms |
| Fixed-size | BM25 + cross-encoder | 0.6390 | 0.6534 | 0.7946 | 500.00 ms | 574.77 ms |
| Fixed-size | BM25 + dense RRF | 0.2641 | 0.3339 | 0.5893 | 177.00 ms | 184.75 ms |
| Fixed-size | Hybrid + cross-encoder | 0.6402 | 0.6635 | 0.8214 | 688.37 ms | 738.96 ms |
| Recursive | BM25 | 0.4285 | 0.4740 | 0.6696 | 4.10 ms | 5.65 ms |
| Recursive | BM25 + cross-encoder | 0.6008 | 0.6177 | 0.7679 | 510.37 ms | 555.04 ms |
| Recursive | BM25 + dense RRF | 0.3382 | 0.3692 | 0.5625 | 194.47 ms | 212.63 ms |
| Recursive | Hybrid + cross-encoder | 0.5813 | 0.5994 | 0.7500 | 704.08 ms | 749.84 ms |
| Sentence-window | BM25 | 0.4178 | 0.4337 | 0.5536 | 9.46 ms | 13.41 ms |
| Sentence-window | BM25 + cross-encoder | 0.6389 | 0.6090 | 0.6696 | 476.59 ms | 562.73 ms |
| Sentence-window | BM25 + dense RRF | 0.3805 | 0.3746 | 0.5238 | 394.31 ms | 470.61 ms |
| Sentence-window | Hybrid + cross-encoder | 0.5970 | 0.5840 | 0.6577 | 973.85 ms | 1,114.41 ms |

The paired BM25-reranked minus BM25 differences were:

| Chunk strategy | MRR difference (95% CI) | nDCG difference (95% CI) | Recall difference (95% CI) |
| --- | --- | --- | --- |
| Fixed-size | +0.2027 [+0.1011, +0.3029] | +0.1729 [+0.0978, +0.2450] | +0.1071 [+0.0446, +0.1875] |
| Recursive | +0.1723 [+0.0779, +0.2725] | +0.1437 [+0.0704, +0.2231] | +0.0982 [+0.0089, +0.1875] |
| Sentence-window | +0.2211 [+0.1321, +0.3174] | +0.1753 [+0.1065, +0.2498] | +0.1161 [+0.0446, +0.1935] |

The large development gains did not transfer clearly to the held-out set. This gap is a reason to retain the simpler default, not a reason to tune on test.

## Does dense fusion add value before reranking?

Compared with BM25 alone, BM25 plus dense RRF reduced k=10 MRR, nDCG, and recall for every chunking strategy in these runs. It also raised p50 latency from 4–9 ms to 177–394 ms. The RRF constant was not swept, so this result applies only to the configured value of 60; it does not establish that all fusion settings perform poorly.

When comparing hybrid-plus-reranker against BM25-plus-reranker, positive differences favor hybrid:

| Chunk strategy | MRR difference (95% CI) | nDCG difference (95% CI) | Recall difference (95% CI) |
| --- | --- | --- | --- |
| Fixed-size | +0.0012 [-0.0083, +0.0113] | +0.0100 [-0.0041, +0.0300] | +0.0268 [+0.0000, +0.0714] |
| Recursive | -0.0195 [-0.0427, -0.0036] | -0.0183 [-0.0407, -0.0025] | -0.0179 [-0.0536, +0.0000] |
| Sentence-window | -0.0419 [-0.1014, +0.0060] | -0.0250 [-0.0768, +0.0221] | -0.0119 [-0.0893, +0.0655] |

Only the fixed-size recall interval reaches zero at its lower bound; the other fixed-size intervals span zero. Recursive hybrid reranking is lower on MRR and nDCG in this development sample. Sentence-window differences remain uncertain. Hybrid reranking also had higher p50 latency than BM25 reranking in all three workspaces.

## Held-out confirmation

The fixed-size BM25-reranked candidate was compared once against fixed-size BM25 on the 18 answerable test queries. Candidate-minus-baseline differences were:

| Cutoff | Metric | Difference (95% CI) |
| ---: | --- | --- |
| 10 | MRR | -0.0295 [-0.1235, +0.0538] |
| 10 | nDCG | -0.0261 [-0.1002, +0.0473] |
| 10 | Recall | -0.0278 [-0.1667, +0.0833] |

All three intervals include zero. The test sample does not confirm the development improvement and also does not establish that reranking is worse. No configuration was retuned using these test results.

## BM25 and RRF parameter sweeps — development only

The fixed-size workspace was used for a coarse BM25 grid sweep on the 56 development questions. The reference was `k1=1.5, b=0.75`; the grid evaluated `k1` in {0.8, 1.2, 1.5, 2.0} and `b` in {0.25, 0.5, 0.75, 1.0}. Each non-default configuration was compared to the reference with paired 95% bootstrap intervals.

No configuration showed a clear improvement in MRR@10 or nDCG@10. The largest positive observed differences were at `k1=0.8, b=1.0`: MRR +0.0079 (95% CI [-0.0360, +0.0536]), nDCG +0.0142 ([-0.0155, +0.0471]), and recall +0.0268 ([0.0000, +0.0714]). The MRR and nDCG intervals span zero. Other settings with slightly positive averages also had intervals spanning zero. Several more extreme settings significantly lowered MRR, including `k1=0.8, b=0.25` (-0.0298, [-0.0654, -0.0005]) and `k1=2.0, b=1.0` (-0.0292, [-0.0585, -0.0065]). The existing BM25 defaults remain `k1=1.5, b=0.75`.

The RRF sweep held BM25 parameters and the embedding model fixed, comparing constants 20, 40, 80, and 100 against 60. RRF 20 had small positive differences in MRR (+0.0065, 95% CI [-0.0063, +0.0202]), nDCG (+0.0101, [-0.0103, +0.0334]), and recall (+0.0268, [-0.0357, +0.0982]); all intervals span zero. RRF 40 was nearly unchanged. RRF 80 had small negative differences with intervals touching or spanning zero. RRF 100 significantly reduced MRR (-0.0098, [-0.0189, -0.0026]) and nDCG (-0.0155, [-0.0307, -0.0027]). Retain RRF 60 as a stable reference; the sweep does not establish that it is optimal.

## Decision and limitations

- Keep workspace-scoped BM25 as the default retrieval behavior.
- Retain BM25 `k1=1.5, b=0.75` and RRF constant 60; the fixed-size dev sweeps did not show a reliable improvement over these references.
- Keep the cross-encoder available as an optional evaluation setting; its development gains came with roughly 0.48–0.51 second p50 retrieval latency for BM25 reranking, and the held-out set was inconclusive.
- Do not enable dense RRF by default based on the current constant and embedding model. The tested hybrid baseline underperformed BM25 and added latency.
- Treat chunk-strategy comparisons as exploratory. The sample contains 56 development and 18 test answerable queries across a small paper corpus; confidence intervals quantify query resampling uncertainty, not corpus diversity.

This is a partial Phase 5 report. BM25 and RRF sweeps cover only the fixed-size workspace. A second embedding-model comparison, query transformation, and the LangChain baseline remain unmeasured. The requested full ablation report should not be considered complete until those planned comparisons are either run or explicitly scoped out with a documented rationale.
