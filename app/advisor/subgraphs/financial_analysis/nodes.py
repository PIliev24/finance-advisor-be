"""Financial analysis sub-graph nodes.

All nodes are pure Python/SQL — no LLM calls. They use the
TransactionRepository directly for data access.
"""

from collections import defaultdict

import structlog

from app.advisor.subgraphs.financial_analysis.state import FinancialAnalysisState
from app.database import get_db
from app.transactions.repository import TransactionRepository

logger = structlog.get_logger()

_DEFAULT_PERIOD_MONTHS = 3


async def fetch_transactions(state: FinancialAnalysisState) -> dict:
    """Fetch recent transactions and aggregate spending by category."""
    period = state.get("period_months", _DEFAULT_PERIOD_MONTHS)
    repo = TransactionRepository(get_db())

    transactions = await repo.get_recent(months=period)
    logger.info("fetch_transactions", count=len(transactions), period_months=period)

    spending_by_category: dict[str, float] = defaultdict(float)
    for txn in transactions:
        if txn.get("type") == "expense":
            cat = txn.get("category", "other")
            spending_by_category[cat] += txn.get("amount", 0)

    return {
        "transactions": transactions,
        "spending_by_category": dict(spending_by_category),
    }


async def compute_spending_trends(state: FinancialAnalysisState) -> dict:
    """Aggregate transactions by month and compute month-over-month changes."""
    transactions = state.get("transactions", [])
    if not transactions:
        return {"spending_trends": []}

    monthly: dict[str, dict[str, float]] = defaultdict(
        lambda: {"total_income": 0.0, "total_expenses": 0.0}
    )

    for txn in transactions:
        date_str = txn.get("date", "")
        if len(date_str) < 7:
            continue
        ym = date_str[:7]
        amount = txn.get("amount", 0)
        if txn.get("type") == "income":
            monthly[ym]["total_income"] += amount
        elif txn.get("type") == "expense":
            monthly[ym]["total_expenses"] += amount

    sorted_months = sorted(monthly.keys())
    trends: list[dict] = []
    prev_expenses = 0.0

    for ym in sorted_months:
        data = monthly[ym]
        mom_change = (
            ((data["total_expenses"] - prev_expenses) / prev_expenses * 100)
            if prev_expenses > 0
            else 0.0
        )
        trends.append({
            "year_month": ym,
            "total_income": round(data["total_income"], 2),
            "total_expenses": round(data["total_expenses"], 2),
            "mom_change_pct": round(mom_change, 2),
        })
        prev_expenses = data["total_expenses"]

    logger.info("compute_spending_trends", months=len(trends))
    return {"spending_trends": trends}


async def compute_income_analysis(state: FinancialAnalysisState) -> dict:
    """Calculate total income, total expenses, and savings rate from transactions."""
    transactions = state.get("transactions", [])

    total_income = 0.0
    total_expenses = 0.0
    income_by_source: dict[str, float] = defaultdict(float)

    for txn in transactions:
        amount = txn.get("amount", 0)
        if txn.get("type") == "income":
            total_income += amount
            income_by_source[txn.get("category", "other")] += amount
        elif txn.get("type") == "expense":
            total_expenses += amount

    savings_rate = (
        (total_income - total_expenses) / total_income * 100
        if total_income > 0
        else 0.0
    )

    logger.info(
        "compute_income_analysis",
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        savings_rate=round(savings_rate, 2),
    )
    return {
        "income_summary": dict(income_by_source),
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "savings_rate": round(savings_rate, 2),
    }
