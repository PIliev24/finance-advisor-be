"""Shared schemas for the advisor system.

Defines all state TypedDicts and data structures used across the entire
advisor orchestration pipeline and its sub-graphs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from operator import add
from typing import Annotated, TypedDict


class Intent(StrEnum):
    general_advice = "general_advice"
    spending_analysis = "spending_analysis"
    budget_check = "budget_check"
    savings_advice = "savings_advice"
    investment_advice = "investment_advice"
    market_query = "market_query"
    import_help = "import_help"


class RuleCategory(StrEnum):
    money_trap = "money_trap"
    smart_habit = "smart_habit"


class RuleSeverity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    name: str
    category: RuleCategory
    triggered: bool
    severity: RuleSeverity
    message: str
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Sub-graph states
# ---------------------------------------------------------------------------


class FinancialAnalysisState(TypedDict, total=False):
    period_months: int
    transactions: list[dict]
    spending_by_category: dict[str, float]
    income_summary: dict[str, float]
    total_income: float
    total_expenses: float
    savings_rate: float
    spending_trends: list[dict]


class BudgetAnalysisState(TypedDict, total=False):
    budgets: list[dict]
    utilization: list[dict]
    alerts: list[dict]


class RuleEvaluationState(TypedDict, total=False):
    financial_context: dict
    rule_results: Annotated[list[RuleResult], add]
    top_findings: list[RuleResult]


class AdviceGenerationState(TypedDict, total=False):
    messages: Annotated[list, add]
    financial_summary: dict
    budget_summary: dict
    rule_findings: list[dict]
    personal_context: dict
    intent: str
    iteration_count: int
    response: str


class MarketAnalysisState(TypedDict, total=False):
    ticker: str
    quote_data: dict
    sentiment_score: float
    sentiment_summary: str
    recommendation: str


# ---------------------------------------------------------------------------
# Parent orchestrator state — superset, all optional
# ---------------------------------------------------------------------------


class AdvisorState(TypedDict, total=False):
    query: str
    intent: Intent
    period_months: int
    # Financial analysis outputs
    transactions: list[dict]
    spending_by_category: dict[str, float]
    income_summary: dict[str, float]
    total_income: float
    total_expenses: float
    savings_rate: float
    spending_trends: list[dict]
    # Budget analysis outputs
    budgets: list[dict]
    utilization: list[dict]
    budget_alerts: list[dict]
    # Rule evaluation outputs
    rule_results: list[RuleResult]
    top_findings: list[RuleResult]
    # Personal context
    personal_context: dict
    # Market analysis (Phase 3)
    ticker: str
    quote_data: dict
    sentiment_score: float
    sentiment_summary: str
    market_recommendation: str
    # Advice generation
    response: str
