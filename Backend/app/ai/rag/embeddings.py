"""Lightweight embedding utility for the RAG knowledge base.

Design rationale
----------------
v1 keeps the embedding approach simple and dependency-free:
  - Each knowledge-base document is chunked into paragraphs.
  - Chunks are stored as plain text with a small metadata dict.
  - Similarity search is done via TF-IDF-style keyword overlap (no vector
    database, no external model call required).

This can be swapped for a real vector store (Chroma, pgvector, etc.) later
without changing the retriever interface — the retriever only calls
``EmbeddingIndex.search(query, k)``.
"""

from __future__ import annotations

import math
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    """Lowercased alphanumeric tokens, length >= 2."""
    return [tok for tok in re.findall(r"[a-z0-9]+", text.lower()) if len(tok) >= 2]


def _tf(tokens: list[str]) -> dict[str, float]:
    counts = Counter(tokens)
    total = max(len(tokens), 1)
    return {tok: count / total for tok, count in counts.items()}


class DocumentChunk:
    """A single retrievable chunk with its source metadata."""

    __slots__ = ("source", "text", "tf_vector")

    def __init__(self, text: str, source: str) -> None:
        self.text = text
        self.source = source
        self.tf_vector: dict[str, float] = _tf(_tokenize(text))


class EmbeddingIndex:
    """In-memory TF-IDF index over document chunks.

    Usage::

        index = EmbeddingIndex()
        index.add_chunks([DocumentChunk(text, source), ...])
        results = index.search("e-waste EPR rules", k=3)
    """

    def __init__(self) -> None:
        self._chunks: list[DocumentChunk] = []
        self._idf: dict[str, float] = {}

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        self._chunks.extend(chunks)
        self._recompute_idf()

    def _recompute_idf(self) -> None:
        n = len(self._chunks)
        if n == 0:
            return
        df: dict[str, int] = {}
        for chunk in self._chunks:
            for tok in chunk.tf_vector:
                df[tok] = df.get(tok, 0) + 1
        self._idf = {tok: math.log((n + 1) / (df_count + 1)) + 1 for tok, df_count in df.items()}

    def _score(self, chunk: DocumentChunk, query_tokens: list[str]) -> float:
        query_tf = _tf(query_tokens)
        score = 0.0
        for tok, qtf in query_tf.items():
            idf = self._idf.get(tok, 0.0)
            ctf = chunk.tf_vector.get(tok, 0.0)
            score += qtf * idf * ctf * idf  # TF-IDF dot product
        return score

    def search(self, query: str, k: int = 5) -> list[tuple[DocumentChunk, float]]:
        """Return the top-k chunks most relevant to *query*, with scores."""
        q_tokens = _tokenize(query)
        if not q_tokens or not self._chunks:
            return []
        scored = [(chunk, self._score(chunk, q_tokens)) for chunk in self._chunks]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(chunk, score) for chunk, score in scored[:k] if score > 0]
