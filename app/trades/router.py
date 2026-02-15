from fastapi import APIRouter

from app.dependencies import APIKey, TradeServiceDep
from app.trades.schemas import TradeRecommendation

router = APIRouter()


@router.get("/recommendations", response_model=list[TradeRecommendation])
async def get_recommendations(
    service: TradeServiceDep,
    _api_key: APIKey,
    tickers: str | None = None,
    risk_tolerance: str = "medium",
) -> list[TradeRecommendation]:
    ticker_list = tickers.split(",") if tickers else None
    return await service.get_recommendations(ticker_list, risk_tolerance)
