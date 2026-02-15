"""Parent orchestrator graph for the advisor pipeline.

Coordinates all sub-graphs:
  classify_intent -> (market path | financial analysis path) -> advice generation -> END
"""

import asyncio
import re

import structlog
from langgraph.graph import END, START, StateGraph

from app.advisor.schemas import AdvisorState, Intent
from app.advisor.subgraphs.advice_generation import advice_generation_graph
from app.advisor.subgraphs.budget_analysis import budget_analysis_graph
from app.advisor.subgraphs.financial_analysis import financial_analysis_graph
from app.advisor.subgraphs.market_analysis import market_analysis_graph
from app.advisor.subgraphs.rule_evaluation import rule_evaluation_graph

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Intent classification keywords
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: dict[Intent, list[str]] = {
    Intent.market_query: [
        "stock",
        "market",
        "ticker",
        "price",
        "quote",
        "trade",
        "invest in",
    ],
    Intent.budget_check: ["budget", "limit", "over budget", "underspent"],
    Intent.spending_analysis: [
        "spending",
        "spent",
        "expenses",
        "where does my money go",
    ],
    Intent.savings_advice: ["save", "saving", "savings rate", "emergency fund"],
    Intent.investment_advice: ["invest", "retirement", "portfolio", "401k", "ira"],
    Intent.import_help: ["import", "csv", "upload", "pdf", "receipt"],
}


# ---------------------------------------------------------------------------
# Orchestrator nodes
# ---------------------------------------------------------------------------


async def classify_intent(state: AdvisorState) -> dict:
    """Classify user intent from query using keyword matching."""
    query = state.get("query", "").lower()

    for intent, keywords in _INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query:
                logger.info("intent_classified", intent=intent, method="keyword")
                return {"intent": intent}

    logger.info("intent_classified", intent=Intent.general_advice, method="default")
    return {"intent": Intent.general_advice}


async def gather_financial_data(state: AdvisorState) -> dict:
    """Run financial analysis and budget analysis sub-graphs in parallel."""
    period = state.get("period_months", 3)

    financial_result, budget_result = await asyncio.gather(
        financial_analysis_graph.ainvoke({"period_months": period}),
        budget_analysis_graph.ainvoke({}),
    )

    return {
        "transactions": financial_result.get("transactions", []),
        "spending_by_category": financial_result.get("spending_by_category", {}),
        "income_summary": financial_result.get("income_summary", {}),
        "total_income": financial_result.get("total_income", 0.0),
        "total_expenses": financial_result.get("total_expenses", 0.0),
        "savings_rate": financial_result.get("savings_rate", 0.0),
        "spending_trends": financial_result.get("spending_trends", []),
        "budgets": budget_result.get("budgets", []),
        "utilization": budget_result.get("utilization", []),
        "budget_alerts": budget_result.get("alerts", []),
    }


async def run_rule_evaluation(state: AdvisorState) -> dict:
    """Build financial context and run rule evaluation sub-graph."""
    financial_context = {
        "spending_by_category": state.get("spending_by_category", {}),
        "total_income": state.get("total_income", 0.0),
        "total_expenses": state.get("total_expenses", 0.0),
        "savings_rate": state.get("savings_rate", 0.0),
        "spending_trends": state.get("spending_trends", []),
        "transactions": state.get("transactions", []),
        "budgets": state.get("budgets", []),
    }

    result = await rule_evaluation_graph.ainvoke({"financial_context": financial_context})

    return {
        "rule_results": result.get("rule_results", []),
        "top_findings": result.get("top_findings", []),
    }


async def enrich_personal_context(state: AdvisorState) -> dict:
    """Fetch user's personal context (life events)."""
    from app.context.repository import ContextRepository
    from app.context.service import ContextService
    from app.database import get_db
    from app.event_store.service import EventStoreService

    db = get_db()
    service = ContextService(EventStoreService(db), ContextRepository(db))
    profile = await service.get_assembled_profile()
    return {"personal_context": profile}


async def run_advice_generation(state: AdvisorState) -> dict:
    """Transform state and run advice generation sub-graph."""
    financial_summary = {
        "total_income": state.get("total_income", 0.0),
        "total_expenses": state.get("total_expenses", 0.0),
        "savings_rate": state.get("savings_rate", 0.0),
        "spending_by_category": state.get("spending_by_category", {}),
        "income_summary": state.get("income_summary", {}),
    }

    budget_summary = {
        "budgets": state.get("utilization", []),
        "alerts": state.get("budget_alerts", []),
    }

    # Convert RuleResult dataclasses to dicts for JSON serialization
    top_findings = state.get("top_findings", [])
    rule_findings: list[dict] = []
    for finding in top_findings:
        if hasattr(finding, "rule_id"):
            rule_findings.append(
                {
                    "rule_id": finding.rule_id,
                    "name": finding.name,
                    "category": str(finding.category),
                    "severity": str(finding.severity),
                    "message": finding.message,
                    "details": finding.details,
                }
            )
        else:
            rule_findings.append(finding)

    advice_input: dict = {
        "financial_summary": financial_summary,
        "budget_summary": budget_summary,
        "rule_findings": rule_findings,
        "personal_context": state.get("personal_context", {}),
        "intent": str(state.get("intent", "general_advice")),
        "messages": [],
        "iteration_count": 0,
    }

    result = await advice_generation_graph.ainvoke(advice_input)
    return {
        "response": result.get("response", "I couldn't generate advice at this time."),
    }


async def run_market_analysis(state: AdvisorState) -> dict:
    """Run market analysis sub-graph for a ticker."""
    query = state.get("query", "")
    ticker = _extract_ticker(query)

    if not ticker:
        return {
            "response": (
                "I couldn't identify a stock ticker in your query. "
                "Please specify a ticker symbol (e.g., AAPL, MSFT)."
            ),
        }

    result = await market_analysis_graph.ainvoke({"ticker": ticker})

    return {
        "ticker": ticker,
        "quote_data": result.get("quote_data", {}),
        "sentiment_score": result.get("sentiment_score", 0.0),
        "sentiment_summary": result.get("sentiment_summary", ""),
        "market_recommendation": result.get("recommendation", ""),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOISE_WORDS = frozenset(
    {
        "I",
        "A",
        "THE",
        "AND",
        "OR",
        "FOR",
        "IN",
        "ON",
        "HOW",
        "IS",
        "MY",
        "ME",
        "DO",
        "CAN",
        "WHAT",
        "ABOUT",
        "OF",
        "TO",
    }
)


def _extract_ticker(query: str) -> str | None:
    """Extract a stock ticker from a query string."""
    matches = re.findall(r"\b([A-Z]{1,5})\b", query)
    tickers = [m for m in matches if m not in _NOISE_WORDS]
    return tickers[0] if tickers else None


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------


def route_after_intent(state: AdvisorState) -> str:
    """Route to appropriate pipeline based on classified intent."""
    intent = state.get("intent")
    if intent == Intent.market_query:
        return "run_market_analysis"
    return "gather_financial_data"


def route_after_market(state: AdvisorState) -> str:
    """Route after market analysis -- end if a response was produced inline."""
    if state.get("response"):
        return END
    return "run_advice_generation"


# ---------------------------------------------------------------------------
# Build the orchestrator graph
# ---------------------------------------------------------------------------

workflow = StateGraph(AdvisorState)

workflow.add_node("classify_intent", classify_intent)
workflow.add_node("gather_financial_data", gather_financial_data)
workflow.add_node("run_rule_evaluation", run_rule_evaluation)
workflow.add_node("enrich_personal_context", enrich_personal_context)
workflow.add_node("run_advice_generation", run_advice_generation)
workflow.add_node("run_market_analysis", run_market_analysis)

workflow.add_edge(START, "classify_intent")
workflow.add_conditional_edges(
    "classify_intent",
    route_after_intent,
    {
        "run_market_analysis": "run_market_analysis",
        "gather_financial_data": "gather_financial_data",
    },
)

workflow.add_edge("gather_financial_data", "run_rule_evaluation")
workflow.add_edge("run_rule_evaluation", "enrich_personal_context")
workflow.add_edge("enrich_personal_context", "run_advice_generation")
workflow.add_edge("run_advice_generation", END)

workflow.add_conditional_edges(
    "run_market_analysis",
    route_after_market,
    {
        "run_advice_generation": "run_advice_generation",
        END: END,
    },
)

advisor_graph = workflow.compile()
