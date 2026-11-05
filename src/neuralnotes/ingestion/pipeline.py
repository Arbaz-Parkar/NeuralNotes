"""In-memory preparation flow from source documents to embedded chunks."""

from dataclasses import dataclass
from pathlib import Path

from neuralnotes.chunking import Chunk, Chunker
from neuralnotes.cleaning import clean_document
from neuralnotes.embeddings import EmbeddingModel, EmbeddingVector
from neuralnotes.parsers import DocumentParser


@dataclass(frozen=True, slots=True)
class EmbeddedChunk:
    """A source-aware chunk paired with its normalized embedding vector."""

    chunk: Chunk
    embedding: EmbeddingVector


@dataclass(frozen=True, slots=True)
class PreparedDocument:
    """Cleaned document metadata and embedded chunks, not yet persisted."""

    document_id: str
    source_path: Path
    title: str | None
    author: str | None
    page_count: int
    chunks: tuple[EmbeddedChunk, ...]


class DocumentIngestionPipeline:
    """Coordinate parser, deterministic cleaning, chunking, and embeddings."""

    def __init__(
        self,
        parser: DocumentParser,
        chunker: Chunker,
        embedder: EmbeddingModel,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder

    def prepare(self, source_path: Path, *, document_id: str) -> PreparedDocument:
        """Prepare one source document into clean, embedded chunks in memory."""
        if not document_id.strip():
            raise ValueError("document_id must not be empty.")

        parsed = self._parser.parse(source_path)
        cleaned = clean_document(parsed)
        chunks = self._chunker.chunk(cleaned, document_id=document_id)
        vectors = self._embedder.embed_documents(tuple(chunk.text for chunk in chunks))
        if len(vectors) != len(chunks):
            raise ValueError("The embedder must return one vector for every chunk.")

        embedded_chunks = tuple(
            EmbeddedChunk(chunk=chunk, embedding=vector)
            for chunk, vector in zip(chunks, vectors, strict=True)
        )
        return PreparedDocument(
            document_id=document_id,
            source_path=cleaned.source_path,
            title=cleaned.title,
            author=cleaned.author,
            page_count=cleaned.page_count,
            chunks=embedded_chunks,
        )
