from pydantic import BaseModel


class TradeRecommendation(BaseModel):
    ticker: str
    action: str  # "buy", "sell", "hold", "watch"
    confidence: float  # 0.0 to 1.0
    current_price: float
    target_price: float | None = None
    stop_loss: float | None = None
    rationale: str
    risk_level: str  # "low", "medium", "high"
    time_horizon: str  # "short_term", "medium_term", "long_term"


class RecommendationRequest(BaseModel):
    tickers: list[str] | None = None  # if None, use watchlist/default tickers
    risk_tolerance: str = "medium"  # "low", "medium", "high"
