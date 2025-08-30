from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from app.agents import search_agent, scrape_agent, summarize_agent, aggregate_agent

class AgentState(TypedDict):
    """
    Represents the state of our agentic workflow.
    """
    query: str
    urls: List[str]
    scraped_articles: List[dict]
    summaries: List[dict]
    final_digest: List[dict]

def build_graph():
    """
    Builds the LangGraph workflow.
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("search", search_agent)
    workflow.add_node("scrape", scrape_agent)
    workflow.add_node("summarize", summarize_agent)
    workflow.add_node("aggregate", aggregate_agent)

    # Define edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "scrape")
    workflow.add_edge("scrape", "summarize")
    workflow.add_edge("summarize", "aggregate")
    workflow.add_edge("aggregate", END)

    # Compile the graph
    app_graph = workflow.compile()
    return app_graph

# Create a single instance of the compiled graph
graph = build_graph()