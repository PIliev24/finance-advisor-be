"""Nodes for the advice-generation sub-graph.

build_context  – assembles the system + user messages from analysis data.
generate_advice – calls the LLM (with tools bound) and tracks iterations.
extract_response – pulls the final text from the last AI message.
"""

import json

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from app.advisor.prompts import ADVICE_SYSTEM_PROMPT
from app.advisor.subgraphs.advice_generation.state import AdviceGenerationState
from app.advisor.tools import advisor_tools

logger = structlog.get_logger()


def _get_llm_with_tools():
    """Create the LLM and bind advisor tools. Imported lazily to avoid circular imports."""
    from app.llm.factory import LLMFactory

    llm = LLMFactory.create()
    return llm.bind_tools(advisor_tools)


async def build_context(state: AdviceGenerationState) -> dict:
    """Inject analysis data into the system prompt and build the message list."""
    financial_summary = json.dumps(state.get("financial_summary", {}), indent=2)
    budget_summary = json.dumps(state.get("budget_summary", {}), indent=2)
    rule_findings = json.dumps(state.get("rule_findings", []), indent=2)
    personal_context = json.dumps(state.get("personal_context", {}), indent=2)

    system_content = ADVICE_SYSTEM_PROMPT.format(
        financial_summary=financial_summary,
        budget_summary=budget_summary,
        rule_findings=rule_findings,
        personal_context=personal_context,
    )

    intent = state.get("intent", "general_advice")
    user_content = (
        f"Based on the financial analysis above, please provide {intent} advice. "
        "Be specific and reference the numbers from the analysis."
    )

    system_msg = SystemMessage(content=system_content)
    user_msg = HumanMessage(content=user_content)

    return {"messages": [system_msg, user_msg]}


async def generate_advice(state: AdviceGenerationState) -> dict:
    """Invoke the LLM with the current message history."""
    llm_with_tools = _get_llm_with_tools()
    response = await llm_with_tools.ainvoke(state["messages"])
    iteration_count = state.get("iteration_count", 0) + 1

    logger.info("advice_llm_called", iteration=iteration_count)
    return {"messages": [response], "iteration_count": iteration_count}


async def extract_response(state: AdviceGenerationState) -> dict:
    """Extract the final text content from the last AI message."""
    messages = state.get("messages", [])
    if not messages:
        return {"response": "I couldn't generate advice at this time."}

    last_message = messages[-1]
    content = getattr(last_message, "content", "")
    if isinstance(content, list):
        # Handle structured content blocks
        text_parts = [
            block.get("text", "") if isinstance(block, dict) else str(block) for block in content
        ]
        content = "\n".join(text_parts)

    return {"response": content or "I couldn't generate advice at this time."}
