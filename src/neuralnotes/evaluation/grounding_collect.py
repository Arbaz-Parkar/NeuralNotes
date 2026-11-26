"""Collect local answer claims and cited passages for human grounding review."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from pydantic import ValidationError

from neuralnotes.evaluation.dataset import load_cases
from neuralnotes.generation.models import GroundedAnswer


def _request_answer(
    endpoint: str, workspace_id: UUID, question: str, top_k: int, timeout: float
) -> GroundedAnswer:
    body = json.dumps(
        {
            "workspace_id": str(workspace_id),
            "query": question,
            "top_k": top_k,
        }
    ).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Answer API returned HTTP {exc.code}: {detail}") from exc
    except (TimeoutError, URLError) as exc:
        raise ValueError(f"Could not reach answer API at {endpoint}: {exc}") from exc
    try:
        return GroundedAnswer.model_validate_json(payload)
    except ValidationError as exc:
        raise ValueError(
            f"Answer API returned an invalid answer payload: {exc}"
        ) from exc


def collect_review_template(
    dataset: Path,
    *,
    split: str,
    workspace_id: UUID,
    endpoint: str,
    top_k: int,
    timeout: float,
    output_path: Path,
) -> tuple[list[dict[str, object]], dict[str, int], list[dict[str, str]]]:
    """Call the answer API for verified answerable cases and flatten their claims."""
    cases = load_cases(dataset, split=split)
    selected = tuple(case for case in cases if case.verified and case.answerable)
    if not selected:
        raise ValueError(f"No verified answerable cases found for split {split!r}.")

    rows: list[dict[str, object]] = []
    counts = {"queries": 0, "abstentions": 0, "claims": 0, "failures": 0}
    failures: list[dict[str, str]] = []
    for index, case in enumerate(selected, start=1):
        print(
            f"[{index}/{len(selected)}] Requesting answer for {case.query_id}",
            flush=True,
        )
        try:
            answer = _request_answer(
                endpoint, workspace_id, case.question, top_k, timeout
            )
        except ValueError as exc:
            counts["failures"] += 1
            failures.append({"query_id": case.query_id, "error": str(exc)})
            print(f"[{index}/{len(selected)}] Failed: {exc}", flush=True)
            continue
        counts["queries"] += 1
        if answer.abstained:
            counts["abstentions"] += 1
            print(f"[{index}/{len(selected)}] Model abstained", flush=True)
            continue
        query_rows = [
            {
                "query_id": case.query_id,
                "question": case.question,
                "claim": claim.text,
                "citations": [
                    {
                        "chunk_id": passage.chunk_id,
                        "document_id": passage.document_id,
                        "page_number": passage.page_number,
                        "text": passage.text,
                    }
                    for passage in claim.citations
                ],
                "label": "",
                "reviewer": "",
                "note": "",
            }
            for claim in answer.claims
        ]
        rows.extend(query_rows)
        if query_rows:
            with output_path.open("a", encoding="utf-8") as output_file:
                output_file.writelines(
                    json.dumps(row, ensure_ascii=False) + "\n" for row in query_rows
                )
                output_file.flush()
        counts["claims"] += len(query_rows)
        print(
            f"[{index}/{len(selected)}] Collected {len(query_rows)} claim(s)",
            flush=True,
        )
    return rows, counts, failures


def main(argv: list[str] | None = None) -> int:
    """Generate a JSONL review template and a collection summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/v1/answer")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--output", type=Path, required=True, help="Output path for the review JSONL."
    )
    args = parser.parse_args(argv)
    if args.top_k < 1 or args.timeout <= 0:
        parser.error("--top-k and --timeout must be positive.")
    if args.output.name == ".jsonl" or args.output.suffix.lower() != ".jsonl":
        parser.error(
            "--output must be a JSONL filename, for example "
            "data/processed/evaluations/grounding/dev-review.jsonl."
        )

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("", encoding="utf-8")
    try:
        _rows, counts, failures = collect_review_template(
            args.dataset,
            split=args.split,
            workspace_id=args.workspace_id,
            endpoint=args.endpoint,
            top_k=args.top_k,
            timeout=args.timeout,
            output_path=output_path,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path = output_path.with_suffix(".summary.json")
    summary = {
        "collected_at": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "split": args.split,
        "workspace_id": str(args.workspace_id),
        **counts,
        "failures_by_query": failures,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote grounding review template to {output_path}")
    print(f"Wrote collection summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
