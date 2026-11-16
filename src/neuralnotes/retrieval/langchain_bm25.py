"""Optional LangChain BM25 adapter used for retrieval baselines."""

from collections.abc import Iterable

from neuralnotes.chunking import Chunk
from neuralnotes.retrieval.bm25 import _tokenize


class LangChainBM25Retriever:
    """Adapt LangChain's BM25Retriever to NeuralNotes chunk identifiers."""

    def __init__(
        self,
        chunks: Iterable[Chunk],
        *,
        k1: float,
        b: float,
        top_k: int,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k must be at least one.")
        try:
            from langchain_community.retrievers.bm25 import BM25Retriever
            from langchain_core.documents import Document
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional LangChain baseline with "
                "`pip install -e .[langchain-baseline]`."
            ) from exc

        documents = [
            Document(page_content=chunk.text, metadata={"chunk_id": chunk.chunk_id})
            for chunk in chunks
        ]
        self._retriever = BM25Retriever.from_documents(
            documents,
            bm25_params={"k1": k1, "b": b},
            preprocess_func=lambda text: list(_tokenize(text)),
            k=top_k,
        )

    def search(self, query: str) -> tuple[str, ...]:
        """Return chunk ids selected by LangChain's BM25 retriever."""
        return tuple(
            str(document.metadata["chunk_id"])
            for document in self._retriever.invoke(query)
        )
