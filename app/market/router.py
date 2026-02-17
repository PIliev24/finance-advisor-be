from fastapi import APIRouter

from app.dependencies import APIKey, MarketServiceDep
from app.market.schemas import MarketAnalysis, StockQuote

router = APIRouter()


@router.get("/quote/{ticker}", response_model=StockQuote)
async def get_quote(ticker: str, service: MarketServiceDep, _api_key: APIKey) -> StockQuote:
    return await service.get_quote(ticker)


@router.get("/analysis/{ticker}", response_model=MarketAnalysis)
async def get_analysis(ticker: str, service: MarketServiceDep, _api_key: APIKey) -> MarketAnalysis:
    return await service.get_analysis(ticker)
