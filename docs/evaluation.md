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

The current results are retrieval smoke checks, not quality findings. Thirty-five manually verified development questions now exist in `data/evaluation/golden.jsonl`, spanning five papers and multiple pages; this small pilot is not a usable benchmark. Expand the verified JSONL question set with evidence recorded by document id, page, and character span. Convert those spans to relevant chunk ids at evaluation time, using a documented overlap threshold, so labels remain usable when chunk boundaries change. Keep development and held-out test questions separate; use the development split for iteration and do not tune against the test split.

The evaluator still needs a larger human-verified question set, a held-out test split, and a tiny CI regression fixture. Do not report a strategy as better based on this thirty-five-question pilot, chunk counts, or search smoke results.

## Current dataset record

Evaluation reports include seeded percentile bootstrap intervals over per-query scores and record the confidence level, resample count, and seed. The paired comparison CLI estimates query-matched candidate-minus-baseline differences. With one query, an interval collapses to a point and is not useful for drawing conclusions.

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

### 8 November pilot smoke run

The BM25 evaluator completed on the five verified DPR development questions in the fixed-size, recursive, and sentence-window workspaces, and both paired comparisons completed before the second paper was labeled. Recall@k and HitRate@k were unchanged. At k=5, paired MRR differences were +0.1333 for both candidates; nDCG differences were +0.0839 for recursive and +0.1000 for sentence-window. These intervals are based on only five queries from one paper and are too unstable to select a strategy. The run confirms report generation and query pairing only. Generated reports remain in ignored local storage. The dataset now has eleven verified development questions across two papers; rerun the comparisons under a new dataset version before using them even as exploratory signals.

`python -m neuralnotes.evaluation.comparison` reads two JSON evaluation run records and pairs their per-query metric values by query id. It rejects different dataset versions, splits, cutoffs, or query sets. Each interval estimates candidate minus baseline, so positive differences favor the candidate. The comparison does not tune parameters and should use `dev` for iteration; keep the held-out `test` split untouched until the final confirmation run.

```powershell
.\.venv\Scripts\python.exe -m neuralnotes.evaluation.comparison `
    --baseline .\data\processed\evaluations\<baseline-run>.json `
    --candidate .\data\processed\evaluations\<candidate-run>.json `
    --output-dir .\data\processed\evaluations\comparisons
```

The command writes timestamped JSON and Markdown summaries with the paired sample count, confidence level, resample count, and seed. A confidence interval spanning zero does not establish a difference; small samples remain unstable even when an interval does not span zero.

## 10 November pilot smoke run — v0.2

The 11 verified development cases across the DPR and Dense X Retrieval papers completed in the fixed-size, recursive, and sentence-window workspaces. Both paired comparisons ran with 2,000 resamples. Recall@k and HitRate@k were unchanged. At k=5, recursive versus fixed-size had +0.1061 MRR (95% interval [0.0000, 0.2576]) and +0.0790 nDCG ([0.0000, 0.1916]); sentence-window versus fixed-size had +0.1061 MRR ([0.0000, 0.2576]) and +0.0742 nDCG ([0.0000, 0.1771]). The sentence-window Precision@5 difference was +0.0727 with interval [-0.0364, 0.2000]. These small, development-only results are a smoke check and do not establish a better strategy. Reports were generated locally under dataset version `dpr-pilot-v0.2` and are not committed.

## 10 November pilot comparison — v0.3

After adding seven R2AG cases, the 18-question development set ran in all three workspaces. In the recursive-versus-fixed comparison, Recall@5 was unchanged; Recall@10 increased by 0.0556 (95% interval [0.0000, 0.1389]) and Recall@20 by 0.0278 ([0.0000, 0.0833]). MRR differences were near zero, and their intervals included zero. In sentence-window versus fixed-size, Recall@5 decreased by 0.1296 ([-0.2778, -0.0278]) and Recall@20 by 0.0648 ([-0.1296, -0.0185]); MRR and nDCG intervals included zero. These are observed results for 18 answerable questions drawn only from the first page of three papers. They are useful for debugging and motivating a larger study, but cannot establish a general chunking winner. The reports remain local under `data/processed/evaluations/`.

## 10 November pilot comparison — v0.4

The expanded set contains 35 verified, answerable development questions across five papers and was evaluated in all three workspaces. The paired sentence-window comparison showed higher precision than fixed-size at k=5 (+0.0571; 95% interval [0.0057, 0.1143]), k=10 (+0.0343; [0.0029, 0.0657]), and k=20 (+0.0157; [0.0014, 0.0300]), alongside lower Recall@20 (-0.1381; [-0.2429, -0.0476]). Its MRR and nDCG intervals included zero. Recursive versus fixed-size had +0.0114 Precision@10 ([0.0029, 0.0229]) and +0.0857 Recall@10 ([-0.0004, 0.2000]); MRR and nDCG intervals included zero. These are pilot estimates from 35 answerable questions across six inspected pages, with no unanswerable or held-out test cases. They show a precision–recall tradeoff in this sample and do not establish a generally better strategy. Reports remain local under `data/processed/evaluations/`.

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

Only use a dataset version after checking the included questions and spans against the source pages. The committed dataset currently contains eleven verified `dev` cases and no held-out `test` cases. Reports include confidence intervals, but these are not enough to establish a winner from such a small and narrow sample. The current CLI supports BM25 and one workspace per run, making it possible to compare the three separately ingested chunking workspaces as the dataset grows.

See [evaluation labeling](evaluation_labeling.md) for the page inspector, evidence review procedure, and dev/test split rules.
