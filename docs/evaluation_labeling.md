# Verifying retrieval evaluation cases

Retrieval scores are meaningful only when the question and evidence labels have been checked against the source. The repository has eighteen verified development cases across three papers as a labeling pilot, which is far too small for evaluation. Candidate questions remain `verified: false` and must not contribute to reports.

## Inspect a source page

Run the local inspector for a paper in the manifest and one-based PDF page number:

```powershell
.\.venv\Scripts\python.exe -m neuralnotes.evaluation.inspect_source `
    --paper-id 2020.emnlp-main.550 `
    --page-number 1
```

The command parses and cleans the PDF using the same pipeline as ingestion, then prints each line with zero-based, end-exclusive character offsets. These page-local offsets match the offsets stored on chunks. The command prints source text to the terminal only; it does not create or commit extracted-paper text.

## Add and verify a case

Evaluation reports now include seeded percentile intervals over per-query metrics. A one-question dataset produces a degenerate interval, which is not useful evidence for selecting a retriever. Keep adding verified questions before interpreting these results.

For each candidate, confirm that the question is answerable from the cited paper, that the reference answer is supported by the selected evidence, and that every document id, page, and character range points to the supporting text. Use `single_passage`, `multi_hop`, `comparison`, or `numeric` for answerable cases. Use `unanswerable` only when the corpus cannot support an answer, with `answerable: false` and an empty evidence list.

Record the answerable evidence as one or more spans in `data/evaluation/golden.jsonl`. Evidence should cover the complete supporting phrase or sentence, not an arbitrarily broad page range. Confirm offsets against the cleaned page display. Set `verified` to true only after checking the question, answer, source, page, and spans. Keep roughly 70% of verified questions in `dev` and 30% in `test`; do not inspect test scores to choose retrieval settings. Include at least 15% unanswerable questions when building the full dataset, even though the current ranking runner excludes them from ranking averages.

Proposed records that still need review should be kept separately from the scored dataset with `verified: false`. Check each candidate against the PDF and its inspector output. When a candidate is accurate, move it into `golden.jsonl`, assign the intended split and final query id, and set `verified: true`. The evaluation loader ignores unverified records.

The JSONL case schema and loader reject malformed ranges, inconsistent answerability labels, and duplicate query ids; the loader returns verified records from only the requested split. A version name should change whenever case content or verification labels change, so reports identify the exact dataset revision.
