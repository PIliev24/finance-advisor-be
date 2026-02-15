import structlog

from app.market.providers.base import MarketDataProvider
from app.market.schemas import MarketAnalysis, StockQuote

logger = structlog.get_logger()


class MarketService:
    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    async def get_quote(self, ticker: str) -> StockQuote:
        ticker = ticker.upper().strip()
        logger.info("market_get_quote", ticker=ticker)
        return await self._provider.get_quote(ticker)

    async def get_analysis(self, ticker: str) -> MarketAnalysis:
        ticker = ticker.upper().strip()
        logger.info("market_get_analysis", ticker=ticker)
        return await self._provider.get_analysis(ticker)
