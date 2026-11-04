"""Fixed-size, overlapping chunk generation."""

from neuralnotes.chunking.models import Chunk, TokenSpan, make_chunk_id
from neuralnotes.chunking.protocols import TokenSpanTokenizer
from neuralnotes.parsers.models import ParsedDocument


class FixedSizeChunker:
    """Create token windows within pages using an injected offset tokenizer."""

    def __init__(
        self,
        tokenizer: TokenSpanTokenizer,
        *,
        chunk_size: int = 400,
        overlap: int = 60,
    ) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1.")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and less than chunk_size.")

        self._tokenizer = tokenizer
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(
        self,
        document: ParsedDocument,
        *,
        document_id: str,
    ) -> tuple[Chunk, ...]:
        """Split each source page into fixed-size token windows."""
        if not document_id.strip():
            raise ValueError("document_id must not be empty.")

        chunks: list[Chunk] = []
        chunk_index = 0
        stride = self._chunk_size - self._overlap

        for page in document.pages:
            spans = tuple(self._tokenizer.token_spans(page.text))
            self._validate_spans(page.text, spans)
            start_token = 0

            while start_token < len(spans):
                end_token = min(start_token + self._chunk_size, len(spans))
                start_char = 0 if start_token == 0 else spans[start_token].start_char
                end_char = (
                    len(page.text)
                    if end_token == len(spans)
                    else spans[end_token].start_char
                )
                chunk_text = page.text[start_char:end_char]
                chunk_id = make_chunk_id(
                    document_id=document_id,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    strategy="fixed_size",
                    text=chunk_text,
                )
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        text=chunk_text,
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        start_char=start_char,
                        end_char=end_char,
                        token_count=end_token - start_token,
                        strategy="fixed_size",
                    )
                )
                chunk_index += 1

                if end_token == len(spans):
                    break
                start_token += stride

        return tuple(chunks)

    @staticmethod
    def _validate_spans(text: str, spans: tuple[TokenSpan, ...]) -> None:
        previous_end = 0
        for span in spans:
            if span.start_char < previous_end or span.end_char > len(text):
                raise ValueError(
                    "Tokenizer spans must be ordered, non-overlapping, and within text."
                )
            previous_end = span.end_char
