"""Budget analysis sub-graph nodes.

All nodes are deterministic — no LLM calls. They use the
BudgetRepository directly for data access.
"""

import structlog

from app.advisor.subgraphs.budget_analysis.state import BudgetAnalysisState
from app.budgets.repository import BudgetRepository
from app.database import get_db

logger = structlog.get_logger()

_WARN_THRESHOLD = 0.80
_EXCEEDED_THRESHOLD = 1.0
_CRITICAL_THRESHOLD = 1.2


async def fetch_budgets(state: BudgetAnalysisState) -> dict:
    """Fetch all active budgets."""
    repo = BudgetRepository(get_db())
    budgets = await repo.list_all(active_only=True)
    logger.info("fetch_budgets", count=len(budgets))
    return {"budgets": budgets}


async def calculate_utilization(state: BudgetAnalysisState) -> dict:
    """Compute current utilization for each budget."""
    budgets = state.get("budgets", [])
    if not budgets:
        return {"utilization": []}

    repo = BudgetRepository(get_db())
    all_usage = await repo.get_all_usage()

    utilization: list[dict] = []
    for budget in budgets:
        category = budget["category"]
        limit = budget.get("monthly_limit", 0)
        usage = all_usage.get(category, 0.0)
        util_ratio = usage / limit if limit > 0 else 0.0

        utilization.append(
            {
                "category": category,
                "monthly_limit": limit,
                "current_usage": round(usage, 2),
                "utilization_pct": round(util_ratio * 100, 2),
                "utilization_ratio": round(util_ratio, 4),
            }
        )

    logger.info("calculate_utilization", budgets_evaluated=len(utilization))
    return {"utilization": utilization}


async def generate_alerts(state: BudgetAnalysisState) -> dict:
    """Apply alert thresholds to utilization and generate alerts."""
    utilization = state.get("utilization", [])
    if not utilization:
        return {"alerts": []}

    alerts: list[dict] = []
    for item in utilization:
        ratio = item.get("utilization_ratio", 0)
        if ratio < _WARN_THRESHOLD:
            continue

        if ratio >= _CRITICAL_THRESHOLD:
            level = "critical"
        elif ratio >= _EXCEEDED_THRESHOLD:
            level = "exceeded"
        else:
            level = "warning"

        alerts.append(
            {
                "category": item["category"],
                "monthly_limit": item["monthly_limit"],
                "current_usage": item["current_usage"],
                "utilization_pct": item["utilization_pct"],
                "alert_level": level,
            }
        )

    logger.info("generate_alerts", alert_count=len(alerts))
    return {"alerts": alerts}
