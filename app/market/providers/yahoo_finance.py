import asyncio
from datetime import UTC, datetime

import structlog
import yfinance as yf

from app.exceptions import AppError, NotFoundError
from app.market.providers.base import MarketDataProvider
from app.market.schemas import MarketAnalysis, StockQuote

logger = structlog.get_logger()


def _fetch_ticker_info(ticker: str) -> dict:
    """Fetch ticker info synchronously (to be run in a thread)."""
    t = yf.Ticker(ticker)
    info = t.info
    has_no_data = (
        not info
        or (
            info.get("trailingPegRatio") is None
            and info.get("regularMarketPrice") is None
            and not info.get("shortName")
            and not info.get("regularMarketPrice")
        )
    )
    if has_no_data:
        raise NotFoundError("Ticker", ticker)
    return info


def _fetch_ticker_history(ticker: str, period: str = "1y") -> list[dict]:
    """Fetch ticker price history synchronously (to be run in a thread)."""
    t = yf.Ticker(ticker)
    hist = t.history(period=period)
    if hist.empty:
        raise NotFoundError("Ticker", ticker)
    return hist.reset_index().to_dict("records")


class YahooFinanceProvider(MarketDataProvider):
    async def get_quote(self, ticker: str) -> StockQuote:
        try:
            info = await asyncio.to_thread(_fetch_ticker_info, ticker)
        except NotFoundError:
            raise
        except Exception as exc:
            logger.error("yfinance_quote_error", ticker=ticker, error=str(exc))
            raise AppError(f"Failed to fetch quote for {ticker}: {exc}") from exc

        price = info.get("regularMarketPrice") or info.get("currentPrice", 0.0)
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose", 0.0)
        change = round(price - prev_close, 4) if price and prev_close else 0.0
        change_pct = round((change / prev_close) * 100, 4) if prev_close else 0.0

        return StockQuote(
            ticker=ticker,
            price=price,
            change=change,
            change_percent=change_pct,
            high=info.get("dayHigh") or info.get("regularMarketDayHigh", 0.0),
            low=info.get("dayLow") or info.get("regularMarketDayLow", 0.0),
            volume=info.get("volume") or info.get("regularMarketVolume", 0),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            timestamp=datetime.now(UTC).isoformat(),
        )

    async def get_analysis(self, ticker: str) -> MarketAnalysis:
        try:
            info = await asyncio.to_thread(_fetch_ticker_info, ticker)
        except NotFoundError:
            raise
        except Exception as exc:
            logger.error("yfinance_analysis_error", ticker=ticker, error=str(exc))
            raise AppError(f"Failed to fetch analysis for {ticker}: {exc}") from exc

        price = info.get("regularMarketPrice") or info.get("currentPrice", 0.0)
        fifty_day = info.get("fiftyDayAverage", 0.0)
        two_hundred_day = info.get("twoHundredDayAverage", 0.0)
        week_52_high = info.get("fiftyTwoWeekHigh", 0.0)
        week_52_low = info.get("fiftyTwoWeekLow", 0.0)

        rsi_signal = _compute_rsi_signal(price, fifty_day, two_hundred_day)
        trend = _compute_trend(price, fifty_day, two_hundred_day)
        summary = _build_analysis_summary(ticker, price, trend, rsi_signal, fifty_day)

        return MarketAnalysis(
            ticker=ticker,
            current_price=price,
            fifty_day_avg=fifty_day,
            two_hundred_day_avg=two_hundred_day,
            week_52_high=week_52_high,
            week_52_low=week_52_low,
            rsi_signal=rsi_signal,
            trend=trend,
            summary=summary,
        )


def _compute_rsi_signal(price: float, fifty_day: float, two_hundred_day: float) -> str:
    """Compute a simplified RSI-like signal from price vs moving averages."""
    if not fifty_day or not two_hundred_day:
        return "neutral"
    avg = (fifty_day + two_hundred_day) / 2
    if not avg:
        return "neutral"
    deviation = (price - avg) / avg
    if deviation < -0.1:
        return "oversold"
    if deviation > 0.1:
        return "overbought"
    return "neutral"


def _compute_trend(price: float, fifty_day: float, two_hundred_day: float) -> str:
    """Determine trend from price vs moving averages."""
    if not fifty_day or not two_hundred_day:
        return "neutral"
    if price > fifty_day > two_hundred_day:
        return "bullish"
    if price < fifty_day < two_hundred_day:
        return "bearish"
    return "neutral"


def _build_analysis_summary(
    ticker: str, price: float, trend: str, rsi_signal: str, fifty_day: float
) -> str:
    """Build a human-readable analysis summary."""
    trend_desc = {"bullish": "upward", "bearish": "downward", "neutral": "sideways"}
    return (
        f"{ticker} is trading at ${price:.2f} with a {trend_desc.get(trend, 'sideways')} trend. "
        f"The RSI signal is {rsi_signal}. "
        f"50-day moving average: ${fifty_day:.2f}."
    )
