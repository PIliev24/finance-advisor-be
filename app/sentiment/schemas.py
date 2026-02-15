from pydantic import BaseModel


class SentimentSource(BaseModel):
    text: str
    source: str  # "twitter", "news", etc.
    sentiment: str  # "positive", "negative", "neutral"
    confidence: float


class SentimentResult(BaseModel):
    ticker: str
    overall_sentiment: str  # "positive", "negative", "neutral"
    sentiment_score: float  # -1.0 to 1.0
    sources_analyzed: int
    sources: list[SentimentSource]
    summary: str
