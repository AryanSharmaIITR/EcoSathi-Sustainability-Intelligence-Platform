import json
import re

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> dict:
    """Groq's models here don't reliably support response_format=json_object
    (fails request-time with images, and general models often wrap answers
    in prose/markdown), so callers prompt for JSON and parse it out of the
    answer, tolerating a markdown code fence around it."""
    fence_match = _JSON_FENCE_RE.search(text)
    candidate = fence_match.group(1) if fence_match else text
    if not fence_match:
        object_match = _JSON_OBJECT_RE.search(candidate)
        if object_match:
            candidate = object_match.group(0)
    return json.loads(candidate)
