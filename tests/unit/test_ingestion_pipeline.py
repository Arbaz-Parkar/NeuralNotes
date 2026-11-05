"""Tests for in-memory document preparation."""

import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from neuralnotes.chunking import FixedSizeChunker, TokenSpan
from neuralnotes.embeddings import EmbeddingVector
from neuralnotes.ingestion import DocumentIngestionPipeline
from neuralnotes.parsers.models import ParsedDocument, ParsedPage


class FakeParser:
    def __init__(self, document: ParsedDocument) -> None:
        self.document = document
        self.received_path: Path | None = None

    def parse(self, source_path: Path) -> ParsedDocument:
        self.received_path = source_path
        return self.document


class WhitespaceTokenizer:
    def token_spans(self, text: str) -> Sequence[TokenSpan]:
        return tuple(
            TokenSpan(match.start(), match.end()) for match in re.finditer(r"\S+", text)
        )


class FakeEmbedder:
    model_name = "fake/model"
    dimension = 2

    def __init__(self, *, mismatch_count: bool = False) -> None:
        self.received_texts: tuple[str, ...] | None = None
        self.mismatch_count = mismatch_count

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> tuple[EmbeddingVector, ...]:
        self.received_texts = tuple(texts)
        count = len(texts) - int(self.mismatch_count)
        return tuple((0.6, 0.8) for _ in range(count))

    def embed_query(self, text: str) -> EmbeddingVector:
        return (0.6, 0.8)


def _document() -> ParsedDocument:
    return ParsedDocument(
        source_path=Path("input.pdf"),
        title="Example paper",
        author="Researcher",
        pages=(
            ParsedPage(page_number=1, text=" alpha    beta "),
            ParsedPage(page_number=2, text="gamma delta"),
        ),
    )


def _pipeline(
    *,
    mismatch_count: bool = False,
) -> tuple[DocumentIngestionPipeline, FakeParser, FakeEmbedder]:
    parser = FakeParser(_document())
    embedder = FakeEmbedder(mismatch_count=mismatch_count)
    chunker = FixedSizeChunker(WhitespaceTokenizer(), chunk_size=2, overlap=0)
    return DocumentIngestionPipeline(parser, chunker, embedder), parser, embedder


def test_pipeline_cleans_chunks_and_embeds_each_page_aware_chunk() -> None:
    pipeline, parser, embedder = _pipeline()

    prepared = pipeline.prepare(Path("input.pdf"), document_id="paper-1")

    assert parser.received_path == Path("input.pdf")
    assert prepared.document_id == "paper-1"
    assert prepared.title == "Example paper"
    assert prepared.author == "Researcher"
    assert prepared.page_count == 2
    assert [item.chunk.text for item in prepared.chunks] == [
        "alpha beta",
        "gamma delta",
    ]
    assert [item.chunk.page_number for item in prepared.chunks] == [1, 2]
    assert [item.embedding for item in prepared.chunks] == [
        (0.6, 0.8),
        (0.6, 0.8),
    ]
    assert embedder.received_texts == ("alpha beta", "gamma delta")


def test_pipeline_rejects_empty_document_id_before_parsing() -> None:
    pipeline, parser, _ = _pipeline()

    with pytest.raises(ValueError, match="document_id"):
        pipeline.prepare(Path("input.pdf"), document_id=" ")

    assert parser.received_path is None


def test_pipeline_rejects_embedder_result_count_mismatch() -> None:
    pipeline, _, _ = _pipeline(mismatch_count=True)

    with pytest.raises(ValueError, match="one vector for every chunk"):
        pipeline.prepare(Path("input.pdf"), document_id="paper-1")
