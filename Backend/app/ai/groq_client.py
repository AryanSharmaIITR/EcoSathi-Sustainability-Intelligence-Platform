import base64

from groq import AsyncGroq

from app.ai.json_utils import extract_json
from app.core.config import get_settings

# Fixed global taxonomy for v1. The spec calls for categories mapped to each
# tenant's *local* waste rules — that needs a waste-category admin data model
# that doesn't exist yet, so real per-tenant mapping is deferred until then.
WASTE_CATEGORIES = ["recyclable", "compostable", "landfill", "hazardous", "e-waste"]

_SYSTEM_PROMPT = (
    "You are a waste-sorting assistant. Identify the item in the image and "
    "classify it into exactly one of these categories: "
    f"{', '.join(WASTE_CATEGORIES)}. "
    "Respond with ONLY a JSON object of the form "
    '{"item_name": "<short specific name of the item, e.g. \'PET Plastic Bottle\'>", '
    '"category": "<one of the categories>", '
    '"disposal_instructions": "<one short, actionable sentence>", '
    '"confidence": <float between 0 and 1>}.'
)

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _client


async def classify_waste_image(image_bytes: bytes, content_type: str) -> dict:
    """Thin internal wrapper around the hosted vision/LLM provider.
    Callers (see app.api.v1.routes.classification) depend on this
    function's return shape, not on Groq directly, so the provider can
    be swapped later without touching callers — per the spec's
    classification architecture requirement.
    """
    settings = get_settings()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{content_type};base64,{encoded}"

    completion = await _get_client().chat.completions.create(
        model=settings.groq_vision_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Classify this item."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        # response_format=json_object is not used: it's unsupported by this
        # model when an image is attached (fails request-time).
        # reasoning_effort="none" turns off this model's chain-of-thought
        # entirely — needed because the hidden thinking is variable-length
        # and would otherwise sometimes exhaust the token budget before any
        # answer is emitted.
        reasoning_effort="none",
        max_completion_tokens=512,
    )

    parsed = extract_json(completion.choices[0].message.content)
    return {
        "item_name": str(parsed.get("item_name", "")).strip() or "Unidentified item",
        "category": str(parsed["category"]).strip().lower(),
        "disposal_instructions": parsed["disposal_instructions"],
        "confidence": float(parsed.get("confidence", 0.0)),
        "model": settings.groq_vision_model,
    }
