from typing import Any, TypedDict


class AgentState(TypedDict):
    """LangGraph state threaded through the orchestration graph. `messages`
    follows the OpenAI/Groq chat-completions message format so it can be
    passed straight back into the next chat.completions.create call."""

    messages: list[dict[str, Any]]
    image_bytes: bytes | None
    image_content_type: str | None
    trace: list[dict[str, Any]]
    iterations: int
