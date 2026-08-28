"""RAG retriever: loads the GoI knowledge base and exposes a single
``retrieve(query)`` function that returns the most relevant text chunks
with their source document metadata.

The index is built once at module load time (a few hundred KB of markdown
at most) and reused across requests.  Rebuilding it is cheap enough that
a future refresh can simply call ``_build_index()`` and swap the module-level
``_INDEX`` variable.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.ai.rag.embeddings import DocumentChunk, EmbeddingIndex

logger = logging.getLogger(__name__)

_KB_DIR = Path(__file__).parent / "knowledge_base"

# Paragraph separator — two or more newlines
_PARAGRAPH_MIN_CHARS = 60  # skip tiny fragments (headings, dividers, table separators)


def _load_document(path: Path) -> list[DocumentChunk]:
    """Split one markdown file into paragraph-level chunks."""
    source = path.stem.replace("_", " ").title()
    raw = path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in raw.split("\n\n") if len(p.strip()) >= _PARAGRAPH_MIN_CHARS]
    return [DocumentChunk(text=para, source=source) for para in paragraphs]


def _build_index() -> EmbeddingIndex:
    index = EmbeddingIndex()
    if not _KB_DIR.is_dir():
        logger.warning("RAG knowledge base directory not found: %s", _KB_DIR)
        return index

    all_chunks: list[DocumentChunk] = []
    for md_file in sorted(_KB_DIR.glob("*.md")):
        chunks = _load_document(md_file)
        logger.debug("Loaded %d chunks from %s", len(chunks), md_file.name)
        all_chunks.extend(chunks)

    index.add_chunks(all_chunks)
    logger.info("RAG index built: %d total chunks from %d documents", len(all_chunks), len(list(_KB_DIR.glob("*.md"))))
    return index


# Module-level singleton — built once, shared across all requests.
_INDEX: EmbeddingIndex = _build_index()


class RetrievedChunk:
    """A retrieval result with text, source, and relevance score."""

    __slots__ = ("score", "source", "text")

    def __init__(self, text: str, source: str, score: float) -> None:
        self.text = text
        self.source = source
        self.score = score

    def to_dict(self) -> dict:
        return {"text": self.text, "source": self.source, "score": round(self.score, 4)}


def retrieve(query: str, k: int = 4) -> list[RetrievedChunk]:
    """Return the top-k most relevant knowledge-base chunks for *query*.

    Args:
        query: Natural-language question or keyword list.
        k:     Maximum number of chunks to return (default 4).

    Returns:
        List of RetrievedChunk objects, sorted by descending relevance.
        Returns an empty list when no chunks score above zero.
    """
    raw_results = _INDEX.search(query, k=k)
    return [RetrievedChunk(text=chunk.text, source=chunk.source, score=score) for chunk, score in raw_results]


def retrieve_as_context(query: str, k: int = 4) -> str:
    """Convenience wrapper that formats retrieved chunks as a prompt-ready
    context block, ready to be inserted into a system prompt.

    Each chunk is prefixed with its source document name so the LLM can
    produce accurate citations.
    """
    chunks = retrieve(query, k=k)
    if not chunks:
        return "No relevant regulatory context was found in the knowledge base."
    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] Source: {chunk.source}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)
