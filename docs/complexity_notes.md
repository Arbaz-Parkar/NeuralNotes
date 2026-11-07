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
