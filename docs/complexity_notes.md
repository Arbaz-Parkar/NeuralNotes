# Complexity notes

This document records the expected time and space costs of the small algorithms
implemented from scratch in NeuralNotes. These are asymptotic estimates, not
benchmarks.

## In-memory BM25 index

The index uses Unicode word tokens after case folding. It stores a mapping from
each term to the chunk positions and term frequencies in which that term occurs.
The default scoring parameters are `k1 = 1.5` and `b = 0.75`.

For a term `t` and chunk `d`, the implementation uses:

```text
idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
score(t, d) = idf(t) * tf(t, d) * (k1 + 1)
             / (tf(t, d) + k1 * (1 - b + b * length(d) / average_length))
```

`N` is the number of chunks and `df(t)` is the number of chunks containing the
term. Query token occurrences each contribute to the score. The core does not
stem words, remove stop words, or connect to a database yet.

Let `T` be the number of tokens in all indexed chunks, `V` the vocabulary size,
`P` the number of term-to-chunk postings, `Q` the number of query tokens, `C` the
number of chunks matching at least one query term, and `K` the requested result
count.

- Build time: expected `O(T)` using hash maps.
- Stored index: `O(V + P + D)` for vocabulary, postings, and chunk metadata,
  where `D` is the number of chunks.
- Search time: `O(Q + C * Q + C log K + K log K)`. Scoring checks query terms
  for each candidate; a min-heap keeps the best `K` results. The final sort is
  over at most `K` results.
- Query working space: `O(C + K)` for candidate positions and the result heap.

The index has no workspace filter. A caller must construct it only from chunks
the requesting workspace is authorized to search. The initial unit tests check
the scoring formula, case-folded tokenization, top-k behavior, stable tie order,
and invalid inputs. Performance and parity with a reference BM25 library have
not been measured; comparison is planned for the retrieval ablation phase.

## Dense cosine retrieval

Dense retrieval stores one embedding vector per chunk. For a query vector `q`
and chunk vector `v`, the index ranks by cosine similarity:

```text
cosine(q, v) = dot(q, v) / (norm(q) * norm(v))
```

For `D` chunks and embedding dimension `E`, this in-memory baseline uses
`O(D * E)` space and `O(D * E + D log K)` search time. It scores every chunk
and sorts the scores; the PostgreSQL HNSW index is not used by this baseline.
This suits the current small local corpus, but should be replaced by database
approximate-nearest-neighbor search as the corpus grows.

## Reciprocal rank fusion

For each unique chunk in each ranked list, reciprocal rank fusion adds
`1 / (c + rank)` using one-based ranks and a configurable constant `c`. It
does not compare BM25 scores with cosine scores; it combines rank positions.
Duplicates within one list contribute only their first position, while results
appearing in multiple lists accumulate evidence. For `L` lists with at most `R`
entries each, fusion takes `O(L * R + U log U)` time and `O(U)` space, where
`U` is the number of unique chunk ids. First-seen order breaks exact score ties
deterministically.

## Cross-encoder reranking

The optional reranker scores each `(query, passage)` pair jointly and sorts a
bounded candidate list by model score. For `C` candidates, its inference cost
is `C` transformer pair evaluations (batched by the model); it is substantially
more expensive than BM25 or vector dot products. The evaluation CLI therefore
reranks only a configured top-candidate pool, warms the model before timing,
and reports per-query retrieval p50/p95 latency. The default model is
`cross-encoder/ms-marco-MiniLM-L6-v2`; its model card lists Apache-2.0 and
describes training for MS MARCO passage ranking.
