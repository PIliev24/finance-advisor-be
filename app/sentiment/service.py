import json
import re

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.exceptions import AppError
from app.sentiment.schemas import SentimentResult, SentimentSource

logger = structlog.get_logger()

_SENTIMENT_PROMPT = (
    "Analyze the current market sentiment for {ticker}. "
    "Based on your knowledge, provide:\n"
    "1. Overall sentiment (positive/negative/neutral)\n"
    "2. A sentiment score from -1.0 (very negative) to 1.0 (very positive)\n"
    "3. Key factors influencing the sentiment\n"
    "4. A brief summary\n\n"
    "Return as JSON with keys: overall_sentiment, sentiment_score, "
    "factors (list of strings), summary"
)


def _parse_llm_json(text: str) -> dict:
    """Parse JSON from LLM response, stripping markdown code block markers if present."""
    cleaned = text.strip()
    # Remove markdown code block markers
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


class SentimentService:
    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def analyze(self, ticker: str) -> SentimentResult:
        ticker = ticker.upper().strip()
        logger.info("sentiment_analyze", ticker=ticker)

        try:
            llm_data = await self._analyze_with_llm(ticker)
        except json.JSONDecodeError as exc:
            logger.error("sentiment_parse_error", ticker=ticker, error=str(exc))
            raise AppError(f"Failed to parse sentiment analysis for {ticker}") from exc
        except Exception as exc:
            logger.error("sentiment_llm_error", ticker=ticker, error=str(exc))
            raise AppError(f"Failed to analyze sentiment for {ticker}: {exc}") from exc

        return self._build_result(ticker, llm_data)

    async def _analyze_with_llm(self, ticker: str) -> dict:
        """Use the LLM to generate sentiment analysis for a ticker."""
        prompt = _SENTIMENT_PROMPT.format(ticker=ticker)
        response = await self._llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content
        content = raw if isinstance(raw, str) else str(raw)
        return _parse_llm_json(content)

    def _build_result(self, ticker: str, llm_data: dict) -> SentimentResult:
        """Build a SentimentResult from LLM-parsed data."""
        factors = llm_data.get("factors", [])
        sources = [
            SentimentSource(
                text=factor,
                source="llm_analysis",
                sentiment=llm_data.get("overall_sentiment", "neutral"),
                confidence=min(abs(llm_data.get("sentiment_score", 0.0)), 1.0),
            )
            for factor in factors
        ]

        return SentimentResult(
            ticker=ticker,
            overall_sentiment=llm_data.get("overall_sentiment", "neutral"),
            sentiment_score=max(-1.0, min(1.0, llm_data.get("sentiment_score", 0.0))),
            sources_analyzed=len(sources),
            sources=sources,
            summary=llm_data.get("summary", "No summary available."),
        )
