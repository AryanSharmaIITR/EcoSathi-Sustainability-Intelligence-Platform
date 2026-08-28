"""Expert Agent 1: Waste Classification, SOP & Compliance Engine.

Capabilities
------------
1. Waste stream classification (organic, plastic, e-waste, hazardous, industrial, etc.)
2. Step-by-step recycling SOP generation
3. RAG-grounded Government of India regulatory references (CPCB, MoEFCC)

Implementation
--------------
Uses a LangGraph state machine:
  agent → [rag_tool | classify_waste_tool] → agent → END

The first turn may call tools; subsequent turns synthesise the final JSON
answer.  Every tool invocation is appended to ``state["trace"]`` so the
orchestrator can log it to the audit trail.
"""

from __future__ import annotations

import json
import logging

from groq import AsyncGroq
from langgraph.graph import END, StateGraph

from app.ai.groq_client import classify_waste_image
from app.ai.json_utils import extract_json
from app.ai.tools.rag_tools import RAG_TOOL_SPEC, call_rag_tool
from app.core.config import get_settings
from app.schemas.agent_io import (
    RegulatoryReference,
    TraceStep,
    WasteCategory,
    WasteComplianceOutput,
)

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 4

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are EcoSathi's Waste & Compliance Expert Agent.
Your job is to classify waste, generate step-by-step recycling SOPs, and cite
the relevant Government of India regulations.

Always use the retrieve_regulatory_context tool to ground your answer in
verified policy text before answering. If an image is available, use
classify_waste first, then retrieve the relevant regulations for that
waste type.

When you have gathered enough context, respond with ONLY a JSON object:
{
  "item_name": "<specific item name>",
  "category": {
    "name": "<category display name>",
    "stream": "<one of: organic|plastic|e-waste|hazardous|industrial|recyclable|landfill|other>"
  },
  "recycling_sop": ["<step 1>", "<step 2>", ...],
  "regulatory_references": [
    {
      "title": "<regulation name>",
      "section": "<rule/section number or null>",
      "authority": "<CPCB|MoEFCC|etc>",
      "relevance_snippet": "<short quote or paraphrase>"
    }
  ],
  "compliance_notes": "<any key obligations, EPR duties, penalties>",
  "confidence": <float 0-1>
}

Do not invent regulations. Only cite what was actually returned by
retrieve_regulatory_context. If no relevant policy was found, set
regulatory_references to [] and say so in compliance_notes.
"""

# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------

from typing import Any, TypedDict, cast


class _WasteAgentState(TypedDict):
    messages: list[dict[str, Any]]
    image_bytes: bytes | None
    image_content_type: str | None
    trace: list[dict[str, Any]]
    iterations: int


# ---------------------------------------------------------------------------
# Tool specs exposed to the model
# ---------------------------------------------------------------------------

_CLASSIFY_WASTE_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "classify_waste",
        "description": (
            "Classify the waste item in the uploaded image. "
            "Returns item_name, category, disposal_instructions, and confidence. "
            "Only call this if an image was provided."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

_TOOL_SPECS = [_CLASSIFY_WASTE_TOOL_SPEC, RAG_TOOL_SPEC]

# ---------------------------------------------------------------------------
# LangGraph nodes
# ---------------------------------------------------------------------------

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _client


async def _agent_node(state: _WasteAgentState) -> _WasteAgentState:
    tool_choice = "auto" if state["iterations"] == 0 else "none"
    completion = await _get_client().chat.completions.create(
        model=get_settings().groq_orchestration_model,
        messages=cast(Any, state["messages"]),
        tools=cast(Any, _TOOL_SPECS),
        tool_choice=tool_choice,
    )
    message = completion.choices[0].message
    state["messages"].append(message.model_dump(exclude_none=True))
    state["iterations"] += 1
    return state


async def _tools_node(state: _WasteAgentState) -> _WasteAgentState:
    last = state["messages"][-1]
    for tool_call in last.get("tool_calls", []):
        name: str = tool_call["function"]["name"]
        arguments: dict = json.loads(tool_call["function"]["arguments"] or "{}")

        if name == "classify_waste":
            if state.get("image_bytes") is None:
                result: dict = {"error": "No image provided."}
            else:
                result = await classify_waste_image(
                    state["image_bytes"],
                    state.get("image_content_type") or "image/jpeg",
                )
        elif name == "retrieve_regulatory_context":
            result = await call_rag_tool(arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}

        state["trace"].append({"tool": name, "arguments": arguments, "result": result})
        state["messages"].append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result),
            }
        )
    return state


def _route_after_agent(state: _WasteAgentState) -> str:
    if state["iterations"] >= _MAX_ITERATIONS:
        return "end"
    last = state["messages"][-1]
    return "tools" if last.get("tool_calls") else "end"


def _build_waste_graph():
    g = StateGraph(_WasteAgentState)
    g.add_node("agent", _agent_node)
    g.add_node("tools", _tools_node)
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")
    return g.compile()


_WASTE_GRAPH = _build_waste_graph()

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_waste_compliance_agent(
    *,
    query: str,
    image_bytes: bytes | None = None,
    image_content_type: str | None = None,
) -> WasteComplianceOutput:
    """Run Expert Agent 1 for a given waste-related query.

    Args:
        query: User's natural-language question.
        image_bytes: Optional uploaded image for visual classification.
        image_content_type: MIME type of the image.

    Returns:
        A fully typed ``WasteComplianceOutput`` with SOP, citations, and trace.
    """
    context_lines = [query]
    if image_bytes is not None:
        context_lines.append(
            "An image has been provided — call classify_waste first to identify the item, "
            "then retrieve relevant regulations."
        )
    else:
        context_lines.append(
            "No image provided — classify based on the text description and retrieve regulations."
        )

    initial_state: _WasteAgentState = {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": " ".join(context_lines)},
        ],
        "image_bytes": image_bytes,
        "image_content_type": image_content_type,
        "trace": [],
        "iterations": 0,
    }

    final_state = await _WASTE_GRAPH.ainvoke(initial_state)
    last_msg = final_state["messages"][-1]
    content = last_msg.get("content") or ""

    try:
        parsed = extract_json(content)
        cat_raw = parsed.get("category", {})
        category = WasteCategory(
            name=cat_raw.get("name", "unknown"),
            stream=cat_raw.get("stream", "other"),
        )
        refs = [
            RegulatoryReference(
                title=r.get("title", ""),
                section=r.get("section"),
                authority=r.get("authority", "Government of India"),
                relevance_snippet=r.get("relevance_snippet", ""),
            )
            for r in parsed.get("regulatory_references", [])
        ]
        return WasteComplianceOutput(
            item_name=str(parsed.get("item_name", "Unidentified item")),
            category=category,
            recycling_sop=list(parsed.get("recycling_sop", [])),
            regulatory_references=refs,
            compliance_notes=parsed.get("compliance_notes"),
            confidence=float(parsed["confidence"]) if parsed.get("confidence") is not None else None,
            trace=[TraceStep(**t) for t in final_state["trace"]],
        )
    except (ValueError, KeyError, TypeError):
        logger.warning("Waste agent could not parse JSON output: %r", content[:300])
        return WasteComplianceOutput(
            item_name="Unknown",
            category=WasteCategory(name="unknown", stream="other"),
            recycling_sop=[content] if content else ["Agent did not produce a structured response."],
            compliance_notes="Agent response was not in the expected JSON format.",
            trace=[TraceStep(**t) for t in final_state["trace"]],
        )
