"""RAG tool — wraps the knowledge-base retriever as a LangGraph-compatible
tool spec so that Expert Agent 1 (Waste & Compliance) can invoke it via the
normal tool-calling interface.

The tool returns raw retrieved chunks so the LLM has full context to
generate regulatory citations and recycling SOPs.
"""

from __future__ import annotations

from app.ai.rag.retriever import retrieve

# Tool spec for the Groq/OpenAI tool-calling API
RAG_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "retrieve_regulatory_context",
        "description": (
            "Search the Government of India regulatory knowledge base "
            "(Solid Waste Management Rules 2016, E-Waste Management Rules 2022, "
            "CPCB Hazardous Waste Guidelines, Plastic Waste Management Rules 2022, "
            "CPCB Recycling Guidelines) and return the most relevant regulatory "
            "passages for the given waste type or compliance query. "
            "Use this to ground recycling SOPs and compliance notes in verified policy text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A specific, targeted query for the knowledge base, e.g. "
                        "'e-waste EPR producer responsibility obligations' or "
                        "'organic waste composting bulk generator rules'."
                    ),
                },
                "k": {
                    "type": "integer",
                    "description": "Number of passages to retrieve (1–6). Default 4.",
                    "minimum": 1,
                    "maximum": 6,
                },
            },
            "required": ["query"],
        },
    },
}


async def call_rag_tool(arguments: dict) -> dict:
    """Execute the RAG retrieval tool.

    Returns a dict with a ``chunks`` list of ``{text, source, score}`` dicts
    that the agent can cite directly in its response.
    """
    query = str(arguments.get("query", "")).strip()
    k = int(arguments.get("k", 4))
    k = max(1, min(k, 6))  # clamp to declared range

    if not query:
        return {"error": "No query provided to retrieve_regulatory_context."}

    chunks = retrieve(query, k=k)
    if not chunks:
        return {
            "available": False,
            "message": "No relevant regulatory passages found for this query.",
            "query": query,
        }

    return {
        "available": True,
        "query": query,
        "chunks": [c.to_dict() for c in chunks],
    }
