"""Data types shared by document chunking strategies."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

ChunkStrategy = Literal["fixed_size", "recursive", "sentence_window"]


def make_chunk_id(
    *,
    document_id: str,
    page_number: int,
    chunk_index: int,
    start_char: int,
    end_char: int,
    strategy: ChunkStrategy,
    text: str,
) -> str:
    """Return a stable SHA-256 id for chunk content and source position."""
    identity_parts = (
        document_id,
        str(page_number),
        str(chunk_index),
        str(start_char),
        str(end_char),
        strategy,
        text,
    )
    digest = sha256()
    for part in identity_parts:
        encoded = part.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="big"))
        digest.update(encoded)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class Chunk:
    """An immutable, page-aware passage with source offsets and chunk metadata."""

    chunk_id: str
    document_id: str
    text: str
    page_number: int
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int
    strategy: ChunkStrategy
    section_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.chunk_id.strip():
            raise ValueError("Chunk ids must not be empty.")
        if not self.document_id.strip():
            raise ValueError("Document ids must not be empty.")
        if not self.text.strip():
            raise ValueError("Chunk text must not be empty.")
        if self.page_number < 1:
            raise ValueError("Chunk page numbers start at 1.")
        if self.chunk_index < 0:
            raise ValueError("Chunk indexes start at 0.")
        if self.start_char < 0 or self.end_char <= self.start_char:
            raise ValueError("Chunk character offsets must define a non-empty range.")
        if self.token_count < 1:
            raise ValueError("Chunk token counts must be positive.")
        if self.strategy not in {"fixed_size", "recursive", "sentence_window"}:
            raise ValueError(f"Unsupported chunk strategy: {self.strategy}.")
