"""Budget analysis sub-graph definition.

Linear pipeline: fetch_budgets -> calculate_utilization -> generate_alerts
"""

from langgraph.graph import END, START, StateGraph

from app.advisor.subgraphs.budget_analysis.nodes import (
    calculate_utilization,
    fetch_budgets,
    generate_alerts,
)
from app.advisor.subgraphs.budget_analysis.state import BudgetAnalysisState

workflow = StateGraph(BudgetAnalysisState)

workflow.add_node("fetch_budgets", fetch_budgets)
workflow.add_node("calculate_utilization", calculate_utilization)
workflow.add_node("generate_alerts", generate_alerts)

workflow.add_edge(START, "fetch_budgets")
workflow.add_edge("fetch_budgets", "calculate_utilization")
workflow.add_edge("calculate_utilization", "generate_alerts")
workflow.add_edge("generate_alerts", END)

budget_analysis_graph = workflow.compile()
