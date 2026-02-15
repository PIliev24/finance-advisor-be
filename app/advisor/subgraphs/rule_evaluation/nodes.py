"""Rule evaluation sub-graph nodes.

Money trap and smart habit checks run in parallel via LangGraph fan-out.
The rule_results field uses an ``Annotated[list, add]`` reducer for safe
parallel merge.
"""

import structlog

from app.advisor.schemas import RuleCategory, RuleResult, RuleSeverity
from app.advisor.subgraphs.rule_evaluation.rules import registry
from app.advisor.subgraphs.rule_evaluation.state import RuleEvaluationState

logger = structlog.get_logger()

_SEVERITY_ORDER = {
    RuleSeverity.critical: 0,
    RuleSeverity.warning: 1,
    RuleSeverity.info: 2,
}
_MAX_TOP_FINDINGS = 10


async def run_money_trap_checks(state: RuleEvaluationState) -> dict:
    """Execute all money-trap rules against the financial context."""
    context = state.get("financial_context", {})
    results = registry.run_all(RuleCategory.money_trap, context)
    logger.info("run_money_trap_checks", rules_evaluated=len(results))
    return {"rule_results": results}


async def run_smart_habit_checks(state: RuleEvaluationState) -> dict:
    """Execute all smart-habit rules against the financial context."""
    context = state.get("financial_context", {})
    results = registry.run_all(RuleCategory.smart_habit, context)
    logger.info("run_smart_habit_checks", rules_evaluated=len(results))
    return {"rule_results": results}


async def prioritize_findings(state: RuleEvaluationState) -> dict:
    """Sort all rule results by severity and return the top triggered findings."""
    all_results: list[RuleResult] = state.get("rule_results", [])

    triggered = [r for r in all_results if r.triggered]
    triggered.sort(key=lambda r: _SEVERITY_ORDER.get(r.severity, 99))
    top = triggered[:_MAX_TOP_FINDINGS]

    logger.info(
        "prioritize_findings",
        total_rules=len(all_results),
        triggered=len(triggered),
        top_count=len(top),
    )
    return {"top_findings": top}
