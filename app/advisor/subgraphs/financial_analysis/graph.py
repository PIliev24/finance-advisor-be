"""Financial analysis sub-graph definition.

Linear pipeline: fetch_transactions -> compute_spending_trends -> compute_income_analysis
"""

from langgraph.graph import END, START, StateGraph

from app.advisor.subgraphs.financial_analysis.nodes import (
    compute_income_analysis,
    compute_spending_trends,
    fetch_transactions,
)
from app.advisor.subgraphs.financial_analysis.state import FinancialAnalysisState

workflow = StateGraph(FinancialAnalysisState)

workflow.add_node("fetch_transactions", fetch_transactions)
workflow.add_node("compute_spending_trends", compute_spending_trends)
workflow.add_node("compute_income_analysis", compute_income_analysis)

workflow.add_edge(START, "fetch_transactions")
workflow.add_edge("fetch_transactions", "compute_spending_trends")
workflow.add_edge("compute_spending_trends", "compute_income_analysis")
workflow.add_edge("compute_income_analysis", END)

financial_analysis_graph = workflow.compile()
