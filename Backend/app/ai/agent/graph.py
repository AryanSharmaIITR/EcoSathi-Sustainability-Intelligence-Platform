import json

from groq import AsyncGroq
from langgraph.graph import END, StateGraph

from app.ai.agent.state import AgentState
from app.ai.agent.tools import TOOL_SPECS, call_tool
from app.core.config import get_settings

# Safety cap on the agent <-> tools loop. With two tools and a cooperative
# model this finishes in 1-2 iterations; this just guards against a model
# that keeps requesting tools indefinitely.
_MAX_ITERATIONS = 5

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _client


async def _agent_node(state: AgentState) -> AgentState:
    settings = get_settings()
    # Only the first turn may call tools. Without this, some models (seen
    # with openai/gpt-oss-120b on Groq) wrap their final JSON answer in a
    # spurious tool call to a nonexistent "JSON" tool once tools have
    # already been used once, which the API rejects outright. Forcing
    # tool_choice="none" on later turns makes finalization reliable.
    tool_choice = "auto" if state["iterations"] == 0 else "none"
    completion = await _get_client().chat.completions.create(
        model=settings.groq_orchestration_model,
        messages=state["messages"],
        tools=TOOL_SPECS,
        tool_choice=tool_choice,
    )
    message = completion.choices[0].message
    state["messages"].append(message.model_dump(exclude_none=True))
    state["iterations"] += 1
    return state


async def _tools_node(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]
    for tool_call in last_message.get("tool_calls", []):
        name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"] or "{}")
        result = await call_tool(
            name,
            arguments,
            image_bytes=state.get("image_bytes"),
            image_content_type=state.get("image_content_type"),
        )
        state["trace"].append({"tool": name, "arguments": arguments, "result": result})
        state["messages"].append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result),
            }
        )
    return state


def _route_after_agent(state: AgentState) -> str:
    if state["iterations"] >= _MAX_ITERATIONS:
        return "end"
    last_message = state["messages"][-1]
    return "tools" if last_message.get("tool_calls") else "end"


def build_agent_graph():
    """Explicit, inspectable graph (not a free-form agent loop): a bounded
    agent<->tools cycle where every tool invocation is captured in
    state["trace"] for audit logging. This is the 'deterministic and
    logged, not a black-box chain' orchestration pattern the spec calls
    for — the graph structure is fixed, only which tools get called (and
    their results) varies per request, and that variation is fully logged.
    """
    graph = StateGraph(AgentState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", _tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()
