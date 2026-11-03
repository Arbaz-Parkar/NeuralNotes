"""Download licensed ACL Anthology PDFs into ignored local storage."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "manifest" / "papers.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "acl_anthology"
ACL_BASE_URL = "https://aclanthology.org"
CC_BY_URL = "https://creativecommons.org/licenses/by/4.0/"
USER_AGENT = "NeuralNotes/0.1 (+https://github.com/Arbaz-Parkar/NeuralNotes)"
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_DELAY_SECONDS = 1.0
MAX_PDF_BYTES = 100 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
PDF_SIGNATURE = b"%PDF-"


class ManifestError(ValueError):
    """Raised when the paper manifest is malformed or not license-verified."""


class DownloadError(RuntimeError):
    """Raised when an ACL Anthology PDF cannot be safely downloaded."""


class RemoteServerError(DownloadError):
    """Raised when the source asks the downloader to stop and retry later."""


@dataclass(frozen=True, slots=True)
class Paper:
    """Manifest metadata needed to identify a paper and preserve provenance."""

    anthology_id: str
    title: str
    year: int
    landing_page_url: str
    pdf_url: str
    license: str
    license_url: str
    license_evidence_url: str
    license_verified_on: str


@dataclass(frozen=True, slots=True)
class DownloadSummary:
    """Counts reported when a manifest download finishes."""

    downloaded: int
    skipped: int
    failed: int


def _required_text(record: dict[str, object], field: str, position: int) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"Paper record {position} has no valid {field!r}.")
    return value


def load_manifest(path: Path = DEFAULT_MANIFEST) -> list[Paper]:
    """Read and validate ACL paper records before making network requests."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Could not read manifest {path}: {exc}") from exc

    if not isinstance(payload, dict) or payload.get("source") != "ACL Anthology":
        raise ManifestError("Manifest source must be 'ACL Anthology'.")

    records = payload.get("papers")
    if not isinstance(records, list) or not records:
        raise ManifestError("Manifest must contain at least one paper.")

    papers: list[Paper] = []
    seen_ids: set[str] = set()
    for position, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ManifestError(f"Paper record {position} must be a JSON object.")

        anthology_id = _required_text(record, "anthology_id", position)
        if re.fullmatch(r"\d{4}\.[a-z0-9-]+\.\d+", anthology_id) is None:
            raise ManifestError(f"Paper record {position} has an invalid Anthology ID.")
        if anthology_id in seen_ids:
            raise ManifestError(f"Duplicate Anthology ID: {anthology_id}.")
        seen_ids.add(anthology_id)

        title = _required_text(record, "title", position)
        year = record.get("year")
        if isinstance(year, bool) or not isinstance(year, int):
            raise ManifestError(f"Paper record {position} has an invalid year.")
        if year != int(anthology_id[:4]):
            raise ManifestError(f"Paper record {position} has a mismatched year.")

        expected_landing_page = f"{ACL_BASE_URL}/{anthology_id}/"
        expected_pdf_url = f"{ACL_BASE_URL}/{anthology_id}.pdf"
        landing_page_url = _required_text(record, "landing_page_url", position)
        pdf_url = _required_text(record, "pdf_url", position)
        if landing_page_url != expected_landing_page:
            raise ManifestError(
                f"Paper record {position} must use its canonical ACL page."
            )
        if pdf_url != expected_pdf_url:
            raise ManifestError(
                f"Paper record {position} must use its canonical ACL PDF URL."
            )

        license_name = _required_text(record, "license", position)
        license_url = _required_text(record, "license_url", position)
        license_evidence_url = _required_text(record, "license_evidence_url", position)
        license_verified_on = _required_text(record, "license_verified_on", position)
        if license_name != "CC-BY-4.0" or license_url != CC_BY_URL:
            raise ManifestError(f"Paper {anthology_id} is not marked as CC BY 4.0.")
        if license_evidence_url != landing_page_url:
            raise ManifestError(
                f"Paper {anthology_id} must cite its ACL page as license evidence."
            )

        papers.append(
            Paper(
                anthology_id=anthology_id,
                title=title,
                year=year,
                landing_page_url=landing_page_url,
                pdf_url=pdf_url,
                license=license_name,
                license_url=license_url,
                license_evidence_url=license_evidence_url,
                license_verified_on=license_verified_on,
            )
        )

    return papers


def _existing_pdf_is_valid(path: Path) -> bool:
    """Return whether an existing file is a PDF; reject corrupt prior files."""
    if not path.exists():
        return False
    try:
        if path.stat().st_size == 0:
            raise DownloadError(f"Existing file is empty: {path}")
        with path.open("rb") as pdf_file:
            if pdf_file.read(len(PDF_SIGNATURE)) != PDF_SIGNATURE:
                raise DownloadError(f"Existing file is not a PDF: {path}")
    except OSError as exc:
        raise DownloadError(f"Could not inspect existing file {path}: {exc}") from exc
    return True


def _validate_download_target(paper: Paper) -> None:
    """Prevent callers from bypassing the manifest's source and license rules."""
    expected_landing_page = f"{ACL_BASE_URL}/{paper.anthology_id}/"
    expected_pdf_url = f"{ACL_BASE_URL}/{paper.anthology_id}.pdf"
    if re.fullmatch(r"\d{4}\.[a-z0-9-]+\.\d+", paper.anthology_id) is None:
        raise DownloadError("Invalid ACL Anthology ID.")
    if paper.year != int(paper.anthology_id[:4]):
        raise DownloadError(f"Publication year does not match {paper.anthology_id}.")
    if paper.landing_page_url != expected_landing_page:
        raise DownloadError(f"Unexpected landing page for {paper.anthology_id}.")
    if paper.pdf_url != expected_pdf_url:
        raise DownloadError(f"Unexpected PDF URL for {paper.anthology_id}.")
    if paper.license != "CC-BY-4.0" or paper.license_url != CC_BY_URL:
        raise DownloadError(f"Paper {paper.anthology_id} is not marked as CC BY 4.0.")
    if paper.license_evidence_url != paper.landing_page_url:
        raise DownloadError(f"License evidence is missing for {paper.anthology_id}.")


def _download_pdf(paper: Paper, destination: Path) -> int:
    """Stream one PDF to a temporary file, then atomically publish it."""
    _validate_download_target(paper)
    request = Request(
        paper.pdf_url,
        headers={"Accept": "application/pdf", "User-Agent": USER_AGENT},
    )
    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            mode="wb",
            prefix=f".{paper.anthology_id}.",
            suffix=".part",
            dir=destination.parent,
            delete=False,
        ) as output_file:
            temporary_path = Path(output_file.name)
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                final_url = urlparse(response.url)
                if (
                    final_url.scheme != "https"
                    or final_url.netloc.lower() != "aclanthology.org"
                ):
                    raise DownloadError("ACL PDF redirected to an unexpected host.")
                if response.status != 200:
                    raise DownloadError(
                        f"ACL returned HTTP {response.status} for {paper.anthology_id}."
                    )

                content_length = response.headers.get("Content-Length")
                expected_bytes: int | None = None
                if content_length is not None:
                    try:
                        expected_bytes = int(content_length)
                    except ValueError as exc:
                        raise DownloadError(
                            "ACL returned an invalid content length."
                        ) from exc
                    if expected_bytes < 0 or expected_bytes > MAX_PDF_BYTES:
                        raise DownloadError(
                            "PDF size is outside the allowed limit for "
                            f"{paper.anthology_id}."
                        )

                first_chunk = response.read(READ_CHUNK_BYTES)
                if not first_chunk.startswith(PDF_SIGNATURE):
                    raise DownloadError(
                        f"ACL response is not a PDF for {paper.anthology_id}."
                    )

                total_bytes = len(first_chunk)
                output_file.write(first_chunk)
                while chunk := response.read(READ_CHUNK_BYTES):
                    total_bytes += len(chunk)
                    if total_bytes > MAX_PDF_BYTES:
                        raise DownloadError(
                            f"PDF exceeds the allowed size for {paper.anthology_id}."
                        )
                    output_file.write(chunk)

                if expected_bytes is not None and total_bytes != expected_bytes:
                    raise DownloadError(
                        f"Downloaded size does not match ACL's content length for "
                        f"{paper.anthology_id}."
                    )

        os.replace(temporary_path, destination)
        return total_bytes
    except HTTPError as exc:
        status = exc.code
        retry_after = exc.headers.get("Retry-After")
        exc.close()
        if status == 429 or status >= 500:
            detail = f"ACL returned HTTP {status}; stopping this download run."
            if retry_after:
                detail += f" Retry-After: {retry_after}."
            raise RemoteServerError(detail) from exc
        raise DownloadError(
            f"ACL returned HTTP {status} for {paper.anthology_id}."
        ) from exc
    except (HTTPException, OSError, ValueError) as exc:
        raise DownloadError(f"Could not download {paper.anthology_id}: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def download_papers(
    papers: Sequence[Paper], output_dir: Path, delay_seconds: float
) -> DownloadSummary:
    """Download papers sequentially, waiting between outbound requests."""
    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative.")
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0
    made_request = False

    for paper in papers:
        destination = output_dir / f"{paper.anthology_id}.pdf"
        try:
            if _existing_pdf_is_valid(destination):
                skipped += 1
                LOGGER.info("Skipping existing PDF: %s", paper.anthology_id)
                continue

            if made_request and delay_seconds:
                time.sleep(delay_seconds)
            made_request = True
            size_bytes = _download_pdf(paper, destination)
            downloaded += 1
            LOGGER.info("Downloaded %s (%s bytes)", paper.anthology_id, size_bytes)
        except RemoteServerError as exc:
            failed += 1
            LOGGER.error("%s", exc)
            break
        except DownloadError as exc:
            failed += 1
            LOGGER.error("%s", exc)

    return DownloadSummary(downloaded=downloaded, skipped=skipped, failed=failed)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ACL Anthology paper downloader from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to the license-checked paper manifest.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Local folder for PDFs (default: ignored data/raw/acl_anthology).",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Pause between PDF requests (default: one second).",
    )
    args = parser.parse_args(argv)
    if args.delay_seconds < 0:
        parser.error("--delay-seconds must be zero or greater.")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        papers = load_manifest(args.manifest)
        summary = download_papers(papers, args.output_dir, args.delay_seconds)
    except (OSError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return 2

    LOGGER.info(
        "Finished: %d downloaded, %d already present, %d failed.",
        summary.downloaded,
        summary.skipped,
        summary.failed,
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
