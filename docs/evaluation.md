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

The current results are retrieval smoke checks, not quality findings. A first manually verified development case now exists in `data/evaluation/golden.jsonl`; it is a labeling pilot, not a usable benchmark. Expand the verified JSONL question set with evidence recorded by document id, page, and character span. Convert those spans to relevant chunk ids at evaluation time, using a documented overlap threshold, so labels remain usable when chunk boundaries change. Keep development and held-out test questions separate; use the development split for iteration and do not tune against the test split.

The evaluator still needs a larger human-verified question set, bootstrap confidence intervals, paired comparison support, a tiny CI regression fixture, and a baseline report. Do not report a strategy as better based on one question, single-paper chunk counts, or search smoke results.

## Current dataset record

Evaluation reports include seeded percentile bootstrap intervals over per-query scores and record the confidence level, resample count, and seed. A paired bootstrap helper estimates query-matched candidate-minus-baseline differences; generating comparison reports from paired runs is not implemented yet. With one query, an interval collapses to a point and is not useful for drawing conclusions.

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

`evaluate_retrieval` accepts a retrieval callback, so the same evidence labels can score BM25 or later retrievers. It returns per-question and macro-averaged values for each requested `k` (default 5, 10, and 20). The BM25 command-line runner and versioned report writer are now implemented; their test and style validation are pending.

## Paired report comparisons

`python -m neuralnotes.evaluation.comparison` reads two JSON evaluation run records and pairs their per-query metric values by query id. It rejects different dataset versions, splits, cutoffs, or query sets. Each interval estimates candidate minus baseline, so positive differences favor the candidate. The comparison does not tune parameters and should use `dev` for iteration; keep the held-out `test` split untouched until the final confirmation run.

```powershell
.\.venv\Scripts\python.exe -m neuralnotes.evaluation.comparison `
    --baseline .\data\processed\evaluations\<baseline-run>.json `
    --candidate .\data\processed\evaluations\<candidate-run>.json `
    --output-dir .\data\processed\evaluations\comparisons
```

The command writes timestamped JSON and Markdown summaries with the paired sample count, confidence level, resample count, and seed. A confidence interval spanning zero does not establish a difference; small samples remain unstable even when an interval does not span zero.

## Local BM25 command

The CLI loads chunks from exactly one PostgreSQL workspace, builds an in-memory BM25 snapshot, scores only verified records from the requested split, and writes a JSON run record plus a Markdown summary. Each run receives a UTC timestamp in its filename, so rerunning does not replace an earlier report. The JSON records the dataset version, workspace, split, evidence threshold, BM25 `k1` and `b`, indexed chunk count, per-query values, and aggregate metrics.

```powershell
.\.venv\Scripts\python.exe -m neuralnotes.evaluation.cli `
    --dataset .\data\evaluation\golden.jsonl `
    --dataset-version v0.1 `
    --split dev `
    --workspace-id 11111111-1111-4111-8111-111111111111 `
    --output-dir .\data\processed\evaluations
```

Only use a dataset version after manually checking the included questions and spans against the source pages. The example path above is a future location; the project does not yet contain a human-verified golden dataset. Reports explicitly state that a single run without confidence intervals cannot establish that one configuration is better. The current CLI supports BM25 and one workspace per run, making it possible to compare the three separately ingested chunking workspaces once verified labels exist.

See [evaluation labeling](evaluation_labeling.md) for the page inspector, evidence review procedure, and dev/test split rules.
