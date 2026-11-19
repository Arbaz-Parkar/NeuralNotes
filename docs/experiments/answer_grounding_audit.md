# Answer grounding audit

## Purpose

Measure whether each generated answer claim is supported by the passage or
passages cited for it. Citation membership is already checked by the answer
service; this audit measures semantic support separately. It is a human-labeled
evaluation, not an automated entailment score.

## Review unit

Review one claim together with the exact cited passage text. Split compound
claims into separate review units when each part could have a different support
label. Do not use uncited retrieved passages when judging a claim.

For a claim with multiple citations, judge whether the cited passages together
support the entire claim. A citation that is merely topically related does not
count as support.

## Labels

- `supported`: the cited passage(s) directly establish the full claim.
- `partially_supported`: they establish only part of the claim or omit a material
  qualification.
- `unsupported`: they do not establish the claim, or contradict it.
- `unverifiable`: the passage or claim is too ambiguous to judge.

Use `unverifiable` sparingly and record why in the note. Do not treat a plausible
claim or a correct citation ID as evidence of support.

## Review record

Store one JSON object per claim in JSONL. Keep the question, claim, citation
identifiers, and exact passage text together so another reviewer can reproduce
the judgment. Example:

```json
{"query_id":"dpr-dev-001","question":"How are dense representations learned in this work?","claim":"Dense representations are learned from a small number of questions and passages by a simple dual-encoder framework.","citations":[{"chunk_id":"850c491a8c45e335442c2aa64879f7383c8faadd69b69f9a1aefd4bf19a20f7f","document_id":"2020.emnlp-main.550","page_number":1,"text":"embeddings are learned from a small number of questions and passages by a simple dual-encoder framework."}],"label":"supported","reviewer":"reviewer-1","note":"The passage directly states the learning setup."}
```

Do not include private reviewer names; use stable pseudonymous reviewer IDs.

## Reporting

Report counts and proportions for all four labels, with the number of reviewed
claims as the denominator. Also report answer-level rates: an answer is fully
supported only when every claim is `supported`; it is partially supported when
at least one claim is partial or unsupported. Exclude `unverifiable` claims from
the supported/unsupported denominator and report their count separately.

When there are two reviewers, report agreement before adjudication and preserve
both original labels. Resolve disagreements with a documented adjudicated label
and note. Keep the split and model configuration with each audit; use dev data
to tune prompts and report final estimates on the held-out test split only once
the protocol is fixed.

## Limits

This measures reviewer judgments for the sampled claims and passages. It does
not prove factual correctness beyond the cited source, and results depend on
the annotation rubric, reviewer agreement, and sample size. Automated model
judges may be explored later, but must be calibrated against this human-labeled
set before their scores are used for comparisons.

## Summarize an audit

After reviewers label the JSONL records, run the report command from the project
root:

```powershell
python -m neuralnotes.evaluation.grounding `
    --input .\data\processed\evaluations\grounding\pilot.jsonl
```

The command validates every record and writes timestamped JSON and Markdown
summaries under `data/processed/evaluations/grounding`. It reports claim label
counts, the supported claim rate, answer label counts, and the fully supported
answer rate. Unverifiable judgments are excluded from the rate denominators and
remain visible in the counts. Add only manually reviewed records to the input
JSONL; model-generated labels are not ground truth.
