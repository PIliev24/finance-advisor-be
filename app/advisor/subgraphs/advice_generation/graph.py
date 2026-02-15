"""Advice generation sub-graph definition.

Topology:
  START -> build_context -> generate_advice --(conditional)--> tool_node | extract_response
                                  ^                                |
                                  |________________________________|
  extract_response -> END

The tool-calling loop is bounded to 5 iterations.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.advisor.subgraphs.advice_generation.nodes import (
    build_context,
    extract_response,
    generate_advice,
)
from app.advisor.subgraphs.advice_generation.state import AdviceGenerationState
from app.advisor.tools import advisor_tools

_MAX_TOOL_ITERATIONS = 5


def _should_continue(state: AdviceGenerationState) -> str:
    """Route after generate_advice: tool_node if tool calls present, else extract."""
    iteration_count = state.get("iteration_count", 0)
    if iteration_count >= _MAX_TOOL_ITERATIONS:
        return "extract_response"

    messages = state.get("messages", [])
    if not messages:
        return "extract_response"

    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"

    return "extract_response"


workflow = StateGraph(AdviceGenerationState)

workflow.add_node("build_context", build_context)
workflow.add_node("generate_advice", generate_advice)
workflow.add_node("tool_node", ToolNode(advisor_tools))
workflow.add_node("extract_response", extract_response)

workflow.add_edge(START, "build_context")
workflow.add_edge("build_context", "generate_advice")
workflow.add_conditional_edges(
    "generate_advice",
    _should_continue,
    {
        "tool_node": "tool_node",
        "extract_response": "extract_response",
    },
)
workflow.add_edge("tool_node", "generate_advice")
workflow.add_edge("extract_response", END)

advice_generation_graph = workflow.compile()
