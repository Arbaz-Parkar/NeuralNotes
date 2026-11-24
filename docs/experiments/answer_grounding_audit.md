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

## Development pilot (2026-11-24)

The first review covered 20 generated claims from 10 verified development
questions, labeled by one reviewer. Nineteen claims were supported and one was
partially supported, for a supported-claim rate of 0.950 (19/20). At the answer
level, 9 of 10 answers were fully supported and one was partially supported
(0.900 fully supported). There were no unsupported or unverifiable judgments.

This is a small workflow pilot, not a reliable estimate of overall answer
faithfulness. With one reviewer, inter-reviewer agreement and Cohen's kappa
were unavailable. Expand the sample and obtain independent overlapping labels
before using it to calibrate or compare an automated judge. The reviewed JSONL
and generated reports are local evaluation artifacts; this summary records the
result without committing source passage text.

## Expanded development sample (2026-11-24)

The review was expanded to 40 claims across 18 development questions, still
with one reviewer. Thirty-seven claims were supported, two were partially
supported, and one was unsupported. The supported-claim rate was 0.925 (37/40).
At the answer level, 15 of 18 answers were fully supported, two were partially
supported, and one was unsupported; the fully supported answer rate was 0.833.
There were no unverifiable judgments. The unsupported claim cited a passage
from the FLARE paper while answering a question about R2AG.

These results describe this small development sample only. They are not a
held-out test result, and a single reviewer provides no inter-reviewer
agreement or calibration evidence for an automated judge. Keep prompt tuning
on dev data and obtain independent overlapping labels before making broader
faithfulness claims.

## First automated-judge calibration (2026-11-24)

The local `qwen2.5:1.5b` judge predicted `supported` for all 40 claims. Against
the single-reviewer labels (37 supported, two partially supported, one
unsupported), exact agreement was 0.925 (37/40), but Cohen's kappa was 0.000:
the judge assigned only one label, so its apparent agreement came from the
majority class. It missed both partial labels and the unsupported claim. Do not
use this judge for scoring or prompt comparisons in its current form. The
per-claim rationales and confusion matrix are in the local generated report.

An exploratory rerun with `qwen3.5:4b` predicted 37 supported and three
partially supported claims, with no unsupported predictions. Against the same
human labels, it matched 36/40 claims (0.900 exact agreement; Cohen's kappa
approximately 0.289). It correctly marked one of the two partial claims, but
missed the other partial claim and the unsupported claim, and incorrectly
marked two supported claims as partial. This is a small development-only
comparison; `qwen3.5:4b` is also the answer-generation model, so this run is not
an independent-judge result. Neither tested judge is suitable for scoring or
prompt comparisons yet.

## Collect claims for review

Start the local API, then collect verified, answerable questions from the dev
split. This writes one unreviewed JSONL row per generated claim and a summary
with query, abstention, and claim counts:

```powershell
python -m neuralnotes.evaluation.grounding_collect `
    --dataset .\data\evaluation\golden.jsonl `
    --split dev `
    --workspace-id 11111111-1111-4111-8111-111111111111 `
    --output .\data\processed\evaluations\grounding\dev-review.jsonl
```

Review each claim against only its listed citation passages. Fill in `label`,
`reviewer`, and `note` in every JSONL row before passing the file to the report
command. The collector does not assign labels. It saves completed claim rows as
each query finishes and reports failed query IDs in the summary, so successful
answers remain available if some requests fail. Use a filename ending in
`.jsonl`, such as `dev-review.jsonl`; malformed output paths are rejected before
any model calls. Collection on the test split is reserved for a final evaluation
after the prompt and protocol are fixed.

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
