"""Tests for safe, license-aware ACL Anthology downloads."""

import io
import json
from dataclasses import replace
from pathlib import Path
from urllib.error import HTTPError

import pytest

from neuralnotes import downloader

PDF_CONTENT = b"%PDF-1.7\n" + b"paper content " * 6000


def _paper(anthology_id: str = "2024.emnlp-main.1") -> downloader.Paper:
    return downloader.Paper(
        anthology_id=anthology_id,
        title="Example ACL Paper",
        year=int(anthology_id[:4]),
        landing_page_url=f"https://aclanthology.org/{anthology_id}/",
        pdf_url=f"https://aclanthology.org/{anthology_id}.pdf",
        license="CC-BY-4.0",
        license_url=downloader.CC_BY_URL,
        license_evidence_url=f"https://aclanthology.org/{anthology_id}/",
        license_verified_on="2026-11-03",
    )


def _manifest_record() -> dict[str, object]:
    paper = _paper()
    return {
        "anthology_id": paper.anthology_id,
        "title": paper.title,
        "year": paper.year,
        "landing_page_url": paper.landing_page_url,
        "pdf_url": paper.pdf_url,
        "license": paper.license,
        "license_url": paper.license_url,
        "license_evidence_url": paper.license_evidence_url,
        "license_verified_on": paper.license_verified_on,
    }


class FakeResponse:
    """Small context-manager response that returns content in bounded reads."""

    def __init__(
        self,
        content: bytes,
        *,
        url: str = "https://aclanthology.org/2024.emnlp-main.1.pdf",
        content_length: int | None = None,
        status: int = 200,
    ) -> None:
        self.content = content
        self.offset = 0
        self.url = url
        self.status = status
        self.headers: dict[str, str] = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.content)
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def test_load_manifest_keeps_license_and_source_metadata(tmp_path: Path) -> None:
    manifest_path = tmp_path / "papers.json"
    manifest_path.write_text(
        json.dumps({"source": "ACL Anthology", "papers": [_manifest_record()]}),
        encoding="utf-8",
    )

    papers = downloader.load_manifest(manifest_path)

    assert papers == [_paper()]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("license", "CC-BY-NC-SA-3.0"),
        ("pdf_url", "https://example.org/paper.pdf"),
        ("license_evidence_url", "https://example.org/license"),
    ],
)
def test_load_manifest_rejects_unlicensed_or_non_acl_records(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    record = _manifest_record()
    record[field] = value
    manifest_path = tmp_path / "papers.json"
    manifest_path.write_text(
        json.dumps({"source": "ACL Anthology", "papers": [record]}),
        encoding="utf-8",
    )

    with pytest.raises(downloader.ManifestError):
        downloader.load_manifest(manifest_path)


@pytest.mark.parametrize(
    "payload",
    [
        ["not", "an object"],
        {"source": "Other", "papers": [_manifest_record()]},
        {"source": "ACL Anthology", "papers": []},
        {"source": "ACL Anthology", "papers": "not a list"},
        {"source": "ACL Anthology", "papers": [None]},
    ],
)
def test_load_manifest_rejects_invalid_document_structure(
    tmp_path: Path,
    payload: object,
) -> None:
    manifest_path = tmp_path / "papers.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(downloader.ManifestError):
        downloader.load_manifest(manifest_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", ""),
        ("anthology_id", "../../outside"),
        ("year", "2024"),
        ("year", 2023),
        ("landing_page_url", "https://example.org/paper/"),
        ("license_url", "https://example.org/license"),
    ],
)
def test_load_manifest_rejects_mismatched_record_fields(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    record = _manifest_record()
    record[field] = value
    manifest_path = tmp_path / "papers.json"
    manifest_path.write_text(
        json.dumps({"source": "ACL Anthology", "papers": [record]}),
        encoding="utf-8",
    )

    with pytest.raises(downloader.ManifestError):
        downloader.load_manifest(manifest_path)


def test_load_manifest_rejects_duplicate_ids(tmp_path: Path) -> None:
    record = _manifest_record()
    manifest_path = tmp_path / "papers.json"
    manifest_path.write_text(
        json.dumps({"source": "ACL Anthology", "papers": [record, record]}),
        encoding="utf-8",
    )

    with pytest.raises(downloader.ManifestError, match="Duplicate"):
        downloader.load_manifest(manifest_path)


def test_load_manifest_reports_invalid_json(tmp_path: Path) -> None:
    manifest_path = tmp_path / "papers.json"
    manifest_path.write_text("{", encoding="utf-8")

    with pytest.raises(downloader.ManifestError, match="Could not read"):
        downloader.load_manifest(manifest_path)


def test_load_manifest_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(downloader.ManifestError, match="Could not read"):
        downloader.load_manifest(tmp_path / "missing.json")


def test_download_pdf_streams_to_a_complete_local_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(PDF_CONTENT, content_length=len(PDF_CONTENT))

    def fake_urlopen(request: object, timeout: int) -> FakeResponse:
        assert timeout == downloader.REQUEST_TIMEOUT_SECONDS
        assert request.full_url == _paper().pdf_url
        return response

    monkeypatch.setattr(downloader, "urlopen", fake_urlopen)
    destination = tmp_path / f"{_paper().anthology_id}.pdf"

    size_bytes = downloader._download_pdf(_paper(), destination)

    assert destination.read_bytes() == PDF_CONTENT
    assert size_bytes == len(PDF_CONTENT)
    assert not list(tmp_path.glob("*.part"))


def test_download_pdf_rejects_non_pdf_response_and_cleans_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        downloader,
        "urlopen",
        lambda request, timeout: FakeResponse(b"not a PDF"),
    )
    destination = tmp_path / f"{_paper().anthology_id}.pdf"

    with pytest.raises(downloader.DownloadError, match="not a PDF"):
        downloader._download_pdf(_paper(), destination)

    assert not destination.exists()
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (FakeResponse(PDF_CONTENT, url="https://example.org/paper.pdf"), "redirected"),
        (FakeResponse(PDF_CONTENT, status=206), "HTTP 206"),
        (
            FakeResponse(PDF_CONTENT, content_length=downloader.MAX_PDF_BYTES + 1),
            "outside the allowed limit",
        ),
        (
            FakeResponse(PDF_CONTENT, content_length=len(PDF_CONTENT) + 1),
            "does not match",
        ),
    ],
)
def test_download_pdf_rejects_unexpected_responses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    response: FakeResponse,
    error: str,
) -> None:
    monkeypatch.setattr(downloader, "urlopen", lambda request, timeout: response)
    destination = tmp_path / f"{_paper().anthology_id}.pdf"

    with pytest.raises(downloader.DownloadError, match=error):
        downloader._download_pdf(_paper(), destination)

    assert not destination.exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_pdf_rejects_invalid_content_length(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(PDF_CONTENT)
    response.headers["Content-Length"] = "invalid"
    monkeypatch.setattr(downloader, "urlopen", lambda request, timeout: response)
    destination = tmp_path / f"{_paper().anthology_id}.pdf"

    with pytest.raises(downloader.DownloadError, match="invalid content length"):
        downloader._download_pdf(_paper(), destination)

    assert not destination.exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_pdf_revalidates_a_direct_paper_object(tmp_path: Path) -> None:
    unsafe_paper = replace(_paper(), pdf_url="https://example.org/paper.pdf")
    destination = tmp_path / f"{unsafe_paper.anthology_id}.pdf"

    with pytest.raises(downloader.DownloadError, match="Unexpected PDF URL"):
        downloader._download_pdf(unsafe_paper, destination)

    assert not destination.exists()


def test_download_pdf_enforces_limit_while_streaming(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(downloader, "MAX_PDF_BYTES", 10)
    monkeypatch.setattr(
        downloader,
        "urlopen",
        lambda request, timeout: FakeResponse(PDF_CONTENT),
    )
    destination = tmp_path / f"{_paper().anthology_id}.pdf"

    with pytest.raises(downloader.DownloadError, match="exceeds the allowed size"):
        downloader._download_pdf(_paper(), destination)

    assert not destination.exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_pdf_wraps_network_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_urlopen(request: object, timeout: int) -> FakeResponse:
        raise OSError("network unavailable")

    monkeypatch.setattr(downloader, "urlopen", fail_urlopen)
    destination = tmp_path / f"{_paper().anthology_id}.pdf"

    with pytest.raises(downloader.DownloadError, match="network unavailable"):
        downloader._download_pdf(_paper(), destination)

    assert not list(tmp_path.glob("*.part"))


def test_download_papers_skips_a_valid_existing_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / f"{_paper().anthology_id}.pdf"
    destination.write_bytes(PDF_CONTENT)
    monkeypatch.setattr(
        downloader,
        "urlopen",
        lambda request, timeout: pytest.fail("existing PDF should be skipped"),
    )

    summary = downloader.download_papers([_paper()], tmp_path, delay_seconds=0)

    assert summary == downloader.DownloadSummary(downloaded=0, skipped=1, failed=0)


def test_rate_limit_stops_the_remaining_downloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def rate_limited_urlopen(request: object, timeout: int) -> FakeResponse:
        nonlocal calls
        calls += 1
        raise HTTPError(
            url=request.full_url,
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "5"},
            fp=io.BytesIO(),
        )

    monkeypatch.setattr(downloader, "urlopen", rate_limited_urlopen)
    papers = [_paper(), _paper("2024.emnlp-main.2")]

    summary = downloader.download_papers(papers, tmp_path, delay_seconds=0)

    assert calls == 1
    assert summary == downloader.DownloadSummary(downloaded=0, skipped=0, failed=1)


def test_existing_corrupt_file_is_reported_without_network_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / f"{_paper().anthology_id}.pdf"
    destination.write_bytes(b"not a PDF")
    monkeypatch.setattr(
        downloader,
        "urlopen",
        lambda request, timeout: pytest.fail(
            "corrupt local file should not be fetched"
        ),
    )

    summary = downloader.download_papers([_paper()], tmp_path, delay_seconds=0)

    assert summary == downloader.DownloadSummary(downloaded=0, skipped=0, failed=1)


@pytest.mark.parametrize("content", [b"", b"not a PDF"])
def test_existing_invalid_files_are_not_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
) -> None:
    destination = tmp_path / f"{_paper().anthology_id}.pdf"
    destination.write_bytes(content)
    monkeypatch.setattr(
        downloader,
        "urlopen",
        lambda request, timeout: pytest.fail(
            "invalid local file should not be fetched"
        ),
    )

    summary = downloader.download_papers([_paper()], tmp_path, delay_seconds=0)

    assert summary == downloader.DownloadSummary(downloaded=0, skipped=0, failed=1)


def test_download_papers_continues_after_a_missing_paper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_count = 0

    def missing_then_success(request: object, timeout: int) -> FakeResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            raise HTTPError(
                url=request.full_url,
                code=404,
                msg="Not Found",
                hdrs={},
                fp=io.BytesIO(),
            )
        return FakeResponse(
            PDF_CONTENT,
            url="https://aclanthology.org/2024.emnlp-main.2.pdf",
            content_length=len(PDF_CONTENT),
        )

    monkeypatch.setattr(downloader, "urlopen", missing_then_success)

    summary = downloader.download_papers(
        [_paper(), _paper("2024.emnlp-main.2")], tmp_path, delay_seconds=0
    )

    assert request_count == 2
    assert summary == downloader.DownloadSummary(downloaded=1, skipped=0, failed=1)


def test_download_papers_rejects_negative_delay(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        downloader.download_papers([_paper()], tmp_path, delay_seconds=-0.1)


@pytest.mark.parametrize(
    ("summary", "expected_exit_code"),
    [
        (downloader.DownloadSummary(downloaded=1, skipped=0, failed=0), 0),
        (downloader.DownloadSummary(downloaded=0, skipped=0, failed=1), 1),
    ],
)
def test_main_reports_download_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    summary: downloader.DownloadSummary,
    expected_exit_code: int,
) -> None:
    monkeypatch.setattr(downloader, "load_manifest", lambda path: [_paper()])
    monkeypatch.setattr(downloader, "download_papers", lambda *args: summary)

    exit_code = downloader.main(
        ["--manifest", str(tmp_path / "papers.json"), "--delay-seconds", "0"]
    )

    assert exit_code == expected_exit_code


def test_main_reports_manifest_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_to_load(path: Path) -> list[downloader.Paper]:
        raise downloader.ManifestError("bad manifest")

    monkeypatch.setattr(downloader, "load_manifest", fail_to_load)

    exit_code = downloader.main(["--manifest", str(tmp_path / "papers.json")])

    assert exit_code == 2


def test_main_reports_output_directory_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocked_path = tmp_path / "not-a-directory"
    blocked_path.write_text("file", encoding="utf-8")
    monkeypatch.setattr(downloader, "load_manifest", lambda path: [_paper()])

    exit_code = downloader.main(["--output-dir", str(blocked_path)])

    assert exit_code == 2


def test_main_rejects_negative_delay() -> None:
    with pytest.raises(SystemExit) as exc_info:
        downloader.main(["--delay-seconds", "-1"])

    assert exc_info.value.code == 2


def test_download_papers_waits_between_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            FakeResponse(PDF_CONTENT, content_length=len(PDF_CONTENT)),
            FakeResponse(
                PDF_CONTENT,
                url="https://aclanthology.org/2024.emnlp-main.2.pdf",
                content_length=len(PDF_CONTENT),
            ),
        ]
    )
    pauses: list[float] = []
    monkeypatch.setattr(downloader, "urlopen", lambda request, timeout: next(responses))
    monkeypatch.setattr(downloader.time, "sleep", pauses.append)

    summary = downloader.download_papers(
        [_paper(), _paper("2024.emnlp-main.2")], tmp_path, delay_seconds=1.25
    )

    assert summary == downloader.DownloadSummary(downloaded=2, skipped=0, failed=0)
    assert pauses == [1.25]
