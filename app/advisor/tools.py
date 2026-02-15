"""LangChain tools that the advice-generation LLM can call.

Each tool wraps an existing repository/service and is instantiated
with the current DB connection (not injected via FastAPI DI).
"""

from langchain_core.tools import tool


@tool
async def query_transactions(
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Query financial transactions with optional filters.

    Args:
        date_from: Start date in YYYY-MM-DD format.
        date_to: End date in YYYY-MM-DD format.
        category: Transaction category to filter by.
        limit: Max number of results.
    """
    from app.database import get_db
    from app.transactions.repository import TransactionRepository
    from app.transactions.schemas import TransactionFilter

    repo = TransactionRepository(get_db())
    filters = TransactionFilter(
        date_from=date_from, date_to=date_to, category=category, limit=limit
    )
    return await repo.list_filtered(filters)


@tool
async def get_monthly_summary(year_month: str | None = None) -> list[dict]:
    """Get monthly spending/income summary, optionally filtered by year-month (YYYY-MM).

    Args:
        year_month: Optional month to filter by in YYYY-MM format.
    """
    from app.database import get_db
    from app.transactions.repository import TransactionRepository

    repo = TransactionRepository(get_db())
    return await repo.get_summary(year_month)


@tool
async def get_budget_status(category: str | None = None) -> list[dict]:
    """Get budget status including utilization and alerts.

    Args:
        category: Optional category to check a specific budget.
    """
    from app.budgets.repository import BudgetRepository
    from app.budgets.service import BudgetService
    from app.database import get_db
    from app.event_store.service import EventStoreService

    db = get_db()
    service = BudgetService(EventStoreService(db), BudgetRepository(db))
    return await service.get_status(category)


@tool
async def calculate_savings_rate(months: int = 3) -> dict:
    """Calculate savings rate over recent months.

    Args:
        months: Number of recent months to analyze.
    """
    from app.database import get_db
    from app.transactions.repository import TransactionRepository

    repo = TransactionRepository(get_db())
    return await repo.calculate_savings_rate(months)


@tool
async def get_spending_trend(category: str, months: int = 6) -> list[dict]:
    """Get spending trends for a category over recent months.

    Args:
        category: The spending category to analyze.
        months: Number of months to look back.
    """
    from app.database import get_db
    from app.transactions.repository import TransactionRepository

    repo = TransactionRepository(get_db())
    return await repo.get_spending_trend(category, months)


@tool
async def get_stock_quote(ticker: str) -> dict:
    """Get the current stock quote for a ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, MSFT).
    """
    from app.market.providers.yahoo_finance import YahooFinanceProvider
    from app.market.service import MarketService

    service = MarketService(YahooFinanceProvider())
    quote = await service.get_quote(ticker)
    return quote.model_dump()


@tool
async def get_market_sentiment(ticker: str) -> dict:
    """Analyze market sentiment for a stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, MSFT).
    """
    from app.llm.factory import LLMFactory
    from app.sentiment.service import SentimentService

    service = SentimentService(LLMFactory.create())
    result = await service.analyze(ticker)
    return result.model_dump()


@tool
async def get_trade_recommendations(
    tickers: str = "AAPL,MSFT,GOOGL",
    risk_tolerance: str = "medium",
) -> list[dict]:
    """Get trade recommendations for stock tickers.

    Args:
        tickers: Comma-separated ticker symbols.
        risk_tolerance: Risk tolerance level (low, medium, high).
    """
    from app.llm.factory import LLMFactory
    from app.market.providers.yahoo_finance import YahooFinanceProvider
    from app.market.service import MarketService
    from app.sentiment.service import SentimentService
    from app.trades.service import TradeService

    llm = LLMFactory.create()
    market_service = MarketService(YahooFinanceProvider())
    sentiment_service = SentimentService(llm)
    trade_service = TradeService(market_service, sentiment_service, llm)

    ticker_list = [t.strip() for t in tickers.split(",")]
    results = await trade_service.get_recommendations(ticker_list, risk_tolerance)
    return [r.model_dump() for r in results]


advisor_tools = [
    query_transactions,
    get_monthly_summary,
    get_budget_status,
    calculate_savings_rate,
    get_spending_trend,
    get_stock_quote,
    get_market_sentiment,
    get_trade_recommendations,
]

tools_by_name = {t.name: t for t in advisor_tools}
