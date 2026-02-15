import asyncio
import json
import re

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.exceptions import AppError, ValidationError
from app.market.schemas import MarketAnalysis, StockQuote
from app.market.service import MarketService
from app.sentiment.schemas import SentimentResult
from app.sentiment.service import SentimentService
from app.trades.schemas import TradeRecommendation

logger = structlog.get_logger()

_DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
_MAX_TICKERS = 10

_RECOMMENDATION_PROMPT = (
    "Based on the following data for {ticker}, provide a trade recommendation:\n\n"
    "Current Price: ${price}\n"
    "52-Week High: ${high}, Low: ${low}\n"
    "Trend: {trend}\n"
    "Sentiment: {sentiment} (score: {score})\n"
    "User Risk Tolerance: {risk_tolerance}\n\n"
    "Provide recommendation as JSON with: action (buy/sell/hold/watch), "
    "confidence (0-1), target_price, stop_loss, rationale, "
    "risk_level (low/medium/high), time_horizon (short_term/medium_term/long_term)"
)


def _parse_llm_json(text: str) -> dict:
    """Parse JSON from LLM response, stripping markdown code block markers if present."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


class TradeService:
    def __init__(
        self,
        market_service: MarketService,
        sentiment_service: SentimentService,
        llm: BaseChatModel,
    ) -> None:
        self._market = market_service
        self._sentiment = sentiment_service
        self._llm = llm

    async def get_recommendations(
        self,
        tickers: list[str] | None = None,
        risk_tolerance: str = "medium",
    ) -> list[TradeRecommendation]:
        tickers = [t.upper().strip() for t in tickers] if tickers else _DEFAULT_TICKERS
        if len(tickers) > _MAX_TICKERS:
            raise ValidationError(f"Maximum {_MAX_TICKERS} tickers allowed per request")

        if risk_tolerance not in ("low", "medium", "high"):
            raise ValidationError(
                f"Invalid risk_tolerance: {risk_tolerance}. Must be low, medium, or high"
            )

        logger.info("trades_get_recommendations", tickers=tickers, risk_tolerance=risk_tolerance)

        tasks = [
            self._get_recommendation_for_ticker(ticker, risk_tolerance)
            for ticker in tickers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        recommendations = []
        for ticker, result in zip(tickers, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(
                    "trade_recommendation_failed", ticker=ticker, error=str(result)
                )
                continue
            recommendations.append(result)

        return recommendations

    async def _get_recommendation_for_ticker(
        self, ticker: str, risk_tolerance: str
    ) -> TradeRecommendation:
        """Fetch market data and sentiment, then generate a recommendation."""
        analysis, sentiment = await asyncio.gather(
            self._market.get_analysis(ticker),
            self._sentiment.analyze(ticker),
        )

        quote = await self._market.get_quote(ticker)
        return await self._generate_recommendation(
            ticker, quote, analysis, sentiment, risk_tolerance
        )

    async def _generate_recommendation(
        self,
        ticker: str,
        quote: StockQuote,
        analysis: MarketAnalysis,
        sentiment: SentimentResult,
        risk_tolerance: str,
    ) -> TradeRecommendation:
        """Use the LLM to synthesize a trade recommendation."""
        prompt = _RECOMMENDATION_PROMPT.format(
            ticker=ticker,
            price=f"{quote.price:.2f}",
            high=f"{analysis.week_52_high:.2f}",
            low=f"{analysis.week_52_low:.2f}",
            trend=analysis.trend,
            sentiment=sentiment.overall_sentiment,
            score=f"{sentiment.sentiment_score:.2f}",
            risk_tolerance=risk_tolerance,
        )

        try:
            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            content = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )
            data = _parse_llm_json(content)
        except json.JSONDecodeError as exc:
            logger.error("trade_recommendation_parse_error", ticker=ticker, error=str(exc))
            raise AppError(f"Failed to parse recommendation for {ticker}") from exc
        except Exception as exc:
            logger.error("trade_recommendation_llm_error", ticker=ticker, error=str(exc))
            raise AppError(f"Failed to generate recommendation for {ticker}: {exc}") from exc

        return TradeRecommendation(
            ticker=ticker,
            action=data.get("action", "hold"),
            confidence=max(0.0, min(1.0, data.get("confidence", 0.5))),
            current_price=quote.price,
            target_price=data.get("target_price"),
            stop_loss=data.get("stop_loss"),
            rationale=data.get("rationale", "No rationale provided."),
            risk_level=data.get("risk_level", "medium"),
            time_horizon=data.get("time_horizon", "medium_term"),
        )
