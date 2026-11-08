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

## Current dataset record

`EvaluationCase` is the JSONL record schema. Offsets are zero-based and end-exclusive within the source page, matching the current page-local chunk offsets. Every span therefore includes both a document id and one-based page number. `verified` defaults to false; only verified records in the requested `dev` or `test` split are loaded. Answerable questions need at least one evidence span, while unanswerable questions use the `unanswerable` category and have no evidence spans.

```json
{
  "query_id": "dpr-dev-001",
  "question": "What retrieval method does the paper evaluate?",
  "split": "dev",
  "category": "single_passage",
  "answerable": true,
  "evidence": [
    {
      "document_id": "2020.emnlp-main.550",
      "page_number": 1,
      "start_char": 1200,
      "end_char": 1280
    }
  ],
  "reference_answer": "A dense passage retriever.",
  "verified": false
}
```

The example is schema-shaped candidate content only; its question, answer, and offsets are not verified labels and must not be added to the scored dataset without checking the source PDF. The current runner maps an evidence span to any chunk from the same document and page that overlaps at least the configured fraction of the evidence span (default 0.5). A missing match on a verified answerable question is an error, which helps catch stale offsets and parser changes. It excludes unanswerable cases from ranking averages and reports their count separately; answerability and abstention metrics need a later evaluator.

`evaluate_retrieval` accepts a retrieval callback, so the same evidence labels can score BM25 or later retrievers. It returns per-question and macro-averaged values for each requested `k` (default 5, 10, and 20). A command-line runner and versioned report writer are not implemented yet.
