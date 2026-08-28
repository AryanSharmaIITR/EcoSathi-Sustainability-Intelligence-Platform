from app.ai.groq_client import classify_waste_image

# Tool specs handed to the orchestration model (see app.ai.agent.graph) —
# the model decides which of these to invoke, per the spec's "explicit
# tool-calling pattern" requirement for the agent layer.
TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "classify_waste",
            "description": (
                "Classify the waste item in the image the user uploaded. "
                "Returns item_name, category, disposal_instructions, and "
                "confidence. Only usable if an image was actually provided."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_usage_forecast",
            "description": (
                "Get the water/energy usage forecast for this tenant, for "
                "anomaly-aware recommendations. NOT YET IMPLEMENTED — "
                "always returns an 'unavailable' result; do not invent a "
                "forecast if this tool reports unavailable."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_type": {"type": "string", "enum": ["water", "energy"]},
                },
                "required": ["resource_type"],
            },
        },
    },
]


async def call_tool(
    name: str,
    arguments: dict,
    *,
    image_bytes: bytes | None,
    image_content_type: str | None,
) -> dict:
    """Executes one agent-requested tool call. Every call here is logged to
    the audit trail by the caller (see app.api.v1.routes.recommend) — this
    is the seam that keeps the agent traceable rather than a black box."""
    if name == "classify_waste":
        if image_bytes is None:
            return {"error": "No image was provided to classify."}
        return await classify_waste_image(image_bytes, image_content_type or "image/jpeg")

    if name == "get_usage_forecast":
        # Forecasting (a separate workstream) isn't built yet. Say so
        # explicitly rather than fabricating a number — per the spec's
        # "no black-box answers" principle.
        return {
            "available": False,
            "message": "Usage forecasting is not implemented yet.",
            "resource_type": arguments.get("resource_type"),
        }

    return {"error": f"Unknown tool: {name}"}
