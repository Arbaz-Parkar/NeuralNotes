# LangChain BM25 baseline — 2026-11-16

## Goal

Compare NeuralNotes' in-house BM25 implementation with LangChain
Community's `BM25Retriever` using the same verified evaluation cases and corpus.
The comparison checks whether adopting a commonly used library implementation
changes retrieval quality enough to justify replacing the current baseline.

## Setup

- Dataset: `dpr-pilot-v0.15`
- Split: `dev`
- Workspace: `11111111-1111-4111-8111-111111111111`
- Paired queries: 56
- Ranking cutoff: 10
- Candidate: LangChain Community BM25 (`langchain-community==0.4.2`,
  `rank-bm25==0.2.2`)
- Baseline: NeuralNotes BM25
- Comparison: paired percentile bootstrap, 2,000 resamples, seed 0,
  confidence 95%

## Results

Differences below are candidate minus NeuralNotes BM25.

| Metric at 10 | Difference | 95% confidence interval |
| --- | ---: | ---: |
| MRR | -0.0146 | [-0.0748, +0.0458] |
| nDCG | -0.0175 | [-0.0598, +0.0241] |
| Recall | -0.0357 | [-0.0804, +0.0000] |

The candidate's point estimates are slightly lower, but the intervals include
zero. This run does not show a reliable quality difference between the two
implementations.

## Decision

Keep NeuralNotes BM25 as the default. The LangChain implementation did not
demonstrate a retrieval-quality improvement on this dev sample, and adopting it
would add runtime dependencies. Keep the optional implementation available for
reproducibility and comparisons. Do not use this dev result to select a
configuration on the held-out test split.

## Limitations

This is a 56-query dev comparison on one workspace. It does not establish
performance across other corpora, chunking strategies, or larger query sets.
