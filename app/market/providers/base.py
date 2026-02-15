from abc import ABC, abstractmethod

from app.market.schemas import MarketAnalysis, StockQuote


class MarketDataProvider(ABC):
    @abstractmethod
    async def get_quote(self, ticker: str) -> StockQuote: ...

    @abstractmethod
    async def get_analysis(self, ticker: str) -> MarketAnalysis: ...
