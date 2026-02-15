"""Market analysis sub-graph definition.

Linear pipeline: fetch_quote -> analyze_sentiment -> generate_recommendation
"""

from langgraph.graph import END, START, StateGraph

from app.advisor.subgraphs.market_analysis.nodes import (
    analyze_sentiment,
    fetch_quote,
    generate_recommendation,
)
from app.advisor.subgraphs.market_analysis.state import MarketAnalysisState

workflow = StateGraph(MarketAnalysisState)

workflow.add_node("fetch_quote", fetch_quote)
workflow.add_node("analyze_sentiment", analyze_sentiment)
workflow.add_node("generate_recommendation", generate_recommendation)

workflow.add_edge(START, "fetch_quote")
workflow.add_edge("fetch_quote", "analyze_sentiment")
workflow.add_edge("analyze_sentiment", "generate_recommendation")
workflow.add_edge("generate_recommendation", END)

market_analysis_graph = workflow.compile()
