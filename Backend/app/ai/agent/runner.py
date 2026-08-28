import logging

from app.ai.agent.graph import build_agent_graph
from app.ai.json_utils import extract_json
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are EcoSathi's action-orchestration agent for a facilities "
    "manager. Use the available tools to gather whatever information you "
    "can about the current situation, then respond with ONLY a JSON "
    'object of the form {"actions": [{"title": "...", '
    '"priority": "high"|"medium"|"low", "rationale": "...", '
    '"category": "water"|"energy"|"waste"|"general", '
    '"estimated_monthly_impact": <number in INR, or null if you cannot '
    "reasonably estimate one>}]}, ranked by impact, most important "
    "first. If a tool reports it is unavailable, say so plainly in the "
    "relevant rationale rather than inventing data. Do not call the same "
    "tool more than once. "
    "IMPORTANT — category assignment rules: use \"water\" for any action "
    "that primarily reduces or monitors water consumption (irrigation, "
    "leaks, taps, pipes, cooling towers, water recycling); use \"energy\" "
    "for any action that primarily reduces or monitors electricity, fuel, "
    "or thermal energy (lighting, HVAC, solar, generators, appliances); "
    "use \"waste\" for actions about solid/liquid waste segregation, "
    "recycling, or disposal; use \"general\" ONLY when the action "
    "genuinely spans multiple resource types or cannot be classified into "
    "the above three. Never default to \"general\" when a more specific "
    "category applies."
)

_agent_graph = build_agent_graph()


async def run_recommendation_agent(
    *,
    tenant_id: str,
    image_bytes: bytes | None,
    image_content_type: str | None,
) -> dict:
    """Runs the LangGraph orchestration agent for one request and returns
    the ranked action plan plus a trace of every tool call made (each of
    which app.api.v1.routes.recommend audit-logs individually)."""
    settings = get_settings()

    context_lines = [f"Tenant: {tenant_id}."]
    context_lines.append(
        "An image was uploaded and can be classified with classify_waste."
        if image_bytes is not None
        else "No image was uploaded — do not call classify_waste."
    )

    initial_state = {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": " ".join(context_lines)},
        ],
        "image_bytes": image_bytes,
        "image_content_type": image_content_type,
        "trace": [],
        "iterations": 0,
    }

    final_state = await _agent_graph.ainvoke(initial_state)

    last_message = final_state["messages"][-1]
    content = last_message.get("content")
    if not content:
        logger.warning(
            "Orchestration agent did not converge to a final answer for tenant %s",
            tenant_id,
        )
        actions = [
            {
                "title": "Review recommendation manually",
                "priority": "medium",
                "rationale": "The orchestration agent did not reach a final recommendation.",
            }
        ]
    else:
        try:
            actions = extract_json(content)["actions"]
        except (ValueError, KeyError):
            logger.warning("Could not parse agent output as actions JSON: %r", content)
            actions = [
                {"title": "Review recommendation manually", "priority": "medium", "rationale": content}
            ]

    return {
        "actions": actions,
        "trace": final_state["trace"],
        "model": settings.groq_orchestration_model,
    }
