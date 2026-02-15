"""Rule evaluation sub-graph definition.

Parallel fan-out: money-trap and smart-habit checks run concurrently,
then merge into prioritize_findings.

The ``rule_results`` field uses ``Annotated[list[RuleResult], add]``
reducer so that parallel branches safely merge their lists.
"""

from langgraph.graph import END, START, StateGraph

from app.advisor.subgraphs.rule_evaluation.nodes import (
    prioritize_findings,
    run_money_trap_checks,
    run_smart_habit_checks,
)
from app.advisor.subgraphs.rule_evaluation.state import RuleEvaluationState

workflow = StateGraph(RuleEvaluationState)

workflow.add_node("run_money_trap_checks", run_money_trap_checks)
workflow.add_node("run_smart_habit_checks", run_smart_habit_checks)
workflow.add_node("prioritize_findings", prioritize_findings)

# Fan-out: START -> both check nodes in parallel
workflow.add_edge(START, "run_money_trap_checks")
workflow.add_edge(START, "run_smart_habit_checks")

# Fan-in: both check nodes -> prioritize_findings
workflow.add_edge("run_money_trap_checks", "prioritize_findings")
workflow.add_edge("run_smart_habit_checks", "prioritize_findings")

workflow.add_edge("prioritize_findings", END)

rule_evaluation_graph = workflow.compile()
