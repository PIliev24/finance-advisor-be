from fastapi import APIRouter

from app.dependencies import APIKey, SentimentServiceDep
from app.sentiment.schemas import SentimentResult

router = APIRouter()


@router.get("/{ticker}", response_model=SentimentResult)
async def analyze_sentiment(
    ticker: str, service: SentimentServiceDep, _api_key: APIKey
) -> SentimentResult:
    return await service.analyze(ticker)
