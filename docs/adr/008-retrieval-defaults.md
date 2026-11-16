# ADR 008: Keep BM25 as the retrieval default

- **Status:** Accepted
- **Date:** 2026-11-16
- **Supersedes:** No prior ADR; records Phase 5 retrieval decisions

## Context

Phase 5 compared chunking strategies, BM25 parameters, dense retrieval, hybrid
BM25+dense reciprocal rank fusion, cross-encoder reranking, pseudo-relevance
feedback, embedding models, and a LangChain BM25 implementation. The verified
dataset is still small and comes from a narrow set of papers, so development
results are useful for screening experiments but do not establish broad
generalization.

## Decision

- Keep workspace-scoped in-house BM25 as the default retrieval path, using
  `k1=1.5` and `b=0.75`.
- Keep the current fixed-size chunking and MiniLM embedding model as stable
  baselines. Do not promote BGE based only on its positive dense-only dev result.
- Keep dense-only search, hybrid RRF (constant 60), cross-encoder reranking,
  BM25 pseudo-relevance feedback, and LangChain BM25 available as explicit
  evaluation options rather than default behavior.
- Do not select a retrieval configuration from the held-out test split. Any
  proposed change to the defaults needs a preregistered comparison on the
  verified dev set and a one-time confirmation on held-out test data.

## Evidence

- Cross-encoder reranking improved the three ranking metrics on the 56-query
  development set for each chunking strategy, with substantial latency cost.
  The fixed-size test comparison on 18 answerable queries was inconclusive and
  did not confirm a gain.
- Dense RRF at the tested settings underperformed BM25 on development. Reranked
  hybrid retrieval did not show a stable advantage over reranked BM25.
- BM25 parameter and RRF sweeps did not show reliable development gains over
  the reference settings. RRF 100 reduced MRR@10 and nDCG@10.
- Dense-only BGE had positive MRR@10, nDCG@10, and Recall@10 differences over
  MiniLM on development, with paired intervals above zero. On the 18-query
  dense-only held-out comparison, its nDCG@10 difference was +0.1384 (95% CI
  [+0.0392, +0.2343]); MRR@10 was +0.1130 ([-0.0259, +0.2361]) and Recall@10
  was +0.1667 ([0.0000, +0.3333]). This is promising but limited confirmation;
  retain MiniLM as the default until broader corpus coverage is available.
- Pseudo-relevance feedback and LangChain BM25 did not show reliable
  development improvements over in-house BM25.

Detailed metrics, intervals, sample sizes, and latency measurements are in
[`docs/experiments/ablation_study.md`](../experiments/ablation_study.md) and the
individual experiment reports.

## Consequences

- New users retain a lightweight, explainable lexical retrieval default.
- Optional retrieval modes remain available for controlled experiments without
  changing the established default.
- The BGE result and reranking development gains remain limited evidence from a
  small corpus. The current data does not support a broad quality claim.
- Future benchmark growth should prioritize additional independently verified
  questions and papers, especially for the held-out split.
