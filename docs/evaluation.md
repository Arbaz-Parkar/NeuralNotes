# Retrieval evaluation

NeuralNotes has the first pure ranking metrics needed for the Phase 4 evaluation harness. They accept ranked chunk identifiers and a set of relevant identifiers, so they can be tested without PostgreSQL, model downloads, or network access.

Implemented metrics:

- Precision@k: relevant results among the first `k`, divided by `k`.
- Recall@k: relevant results among the first `k`, divided by all labeled relevant results.
- Hit rate@k: whether at least one relevant result appears among the first `k`.
- Reciprocal rank@k: the inverse rank of the first relevant result, or zero when none appears.
- nDCG@k: binary relevance with logarithmic rank discount, normalized against the ideal ordering.

An empty relevance set scores zero for every metric. This avoids silently treating an unlabeled or unanswerable query as a successful retrieval. Dataset validation must distinguish those cases before evaluation: an unanswerable query is a labeled case with no evidence, while a missing label is invalid input.

## Evaluation design still to build

The current results are retrieval smoke checks, not quality findings. Before comparing chunking or retrieval configurations, build a verified JSONL question set whose evidence is recorded by document id and character span. Convert those spans to relevant chunk ids at evaluation time, using a documented overlap threshold, so labels remain usable when chunk boundaries change. Keep development and held-out test questions separate; use the development split for iteration and do not tune against the test split.

The evaluator still needs dataset schemas and validation, span-to-chunk relevance mapping, aggregation across cases, a deterministic runner, versioned JSON/Markdown reports, bootstrap confidence intervals, and a tiny CI regression fixture. Do not report a strategy as better based on the current single-paper chunk counts or search smoke results.
