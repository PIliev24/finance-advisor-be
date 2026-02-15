"""Advisor service — thin wrapper around the compiled advisor graph."""

import json
from collections.abc import AsyncGenerator

import structlog

from app.advisor.orchestrator import advisor_graph

logger = structlog.get_logger()


class AdvisorService:
    """Provides sync and streaming chat methods over the advisor pipeline."""

    async def chat(self, query: str) -> str:
        """Non-streaming chat -- runs the full advisor pipeline."""
        result = await advisor_graph.ainvoke(
            {"query": query},
            {"recursion_limit": 25},
        )
        return result.get("response", "I couldn't generate a response.")

    async def chat_stream(self, query: str) -> AsyncGenerator[dict, None]:
        """SSE streaming chat -- yields events during pipeline execution."""
        yield {"event": "status", "data": json.dumps({"step": "starting"})}

        try:
            async for event in advisor_graph.astream_events(
                {"query": query},
                config={"recursion_limit": 25},
                version="v2",
            ):
                kind = event.get("event")

                if kind == "on_chain_start" and event.get("name"):
                    yield {
                        "event": "status",
                        "data": json.dumps({"step": event["name"]}),
                    }
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        yield {
                            "event": "token",
                            "data": content if isinstance(content, str) else str(content),
                        }
                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output", {})
                    response = output.get("response", "")
                    if response:
                        yield {
                            "event": "response",
                            "data": json.dumps({"response": response}),
                        }
        except Exception as exc:
            logger.error("advisor_stream_error", error=str(exc))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }

        yield {"event": "done", "data": ""}
