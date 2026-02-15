"""Nodes for the market-analysis sub-graph.

fetch_quote             – retrieves a stock quote via MarketService.
analyze_sentiment       – runs LLM-based sentiment analysis.
generate_recommendation – produces a trade recommendation.
"""

import structlog

from app.advisor.subgraphs.market_analysis.state import MarketAnalysisState

logger = structlog.get_logger()


async def fetch_quote(state: MarketAnalysisState) -> dict:
    """Fetch the current stock quote for the ticker."""
    from app.market.providers.yahoo_finance import YahooFinanceProvider
    from app.market.service import MarketService

    ticker = state["ticker"]
    service = MarketService(YahooFinanceProvider())
    quote = await service.get_quote(ticker)

    logger.info("market_quote_fetched", ticker=ticker, price=quote.price)
    return {"quote_data": quote.model_dump()}


async def analyze_sentiment(state: MarketAnalysisState) -> dict:
    """Analyze market sentiment for the ticker using the LLM."""
    from app.llm.factory import LLMFactory
    from app.sentiment.service import SentimentService

    ticker = state["ticker"]
    service = SentimentService(LLMFactory.create())
    result = await service.analyze(ticker)

    logger.info(
        "market_sentiment_analyzed",
        ticker=ticker,
        score=result.sentiment_score,
    )
    return {
        "sentiment_score": result.sentiment_score,
        "sentiment_summary": result.summary,
    }


async def generate_recommendation(state: MarketAnalysisState) -> dict:
    """Generate a trade recommendation for the ticker."""
    from app.llm.factory import LLMFactory
    from app.market.providers.yahoo_finance import YahooFinanceProvider
    from app.market.service import MarketService
    from app.sentiment.service import SentimentService
    from app.trades.service import TradeService

    ticker = state["ticker"]
    market_service = MarketService(YahooFinanceProvider())
    sentiment_service = SentimentService(LLMFactory.create())
    trade_service = TradeService(market_service, sentiment_service, LLMFactory.create())

    recommendations = await trade_service.get_recommendations(
        tickers=[ticker], risk_tolerance="medium"
    )

    if recommendations:
        rec = recommendations[0]
        logger.info(
            "market_recommendation_generated",
            ticker=ticker,
            action=rec.action,
        )
        return {"recommendation": rec.rationale}

    logger.warning("market_recommendation_empty", ticker=ticker)
    return {"recommendation": f"Unable to generate recommendation for {ticker}."}
