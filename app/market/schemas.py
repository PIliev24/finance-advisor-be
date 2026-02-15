from pydantic import BaseModel


class StockQuote(BaseModel):
    ticker: str
    price: float
    change: float
    change_percent: float
    high: float
    low: float
    volume: int
    market_cap: float | None = None
    pe_ratio: float | None = None
    timestamp: str


class MarketAnalysis(BaseModel):
    ticker: str
    current_price: float
    fifty_day_avg: float
    two_hundred_day_avg: float
    week_52_high: float
    week_52_low: float
    rsi_signal: str  # "oversold", "neutral", "overbought"
    trend: str  # "bullish", "bearish", "neutral"
    summary: str
