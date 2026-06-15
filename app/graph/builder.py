"""Graph builder - creates LangGraph workflow"""
from langgraph.graph import StateGraph, END

from app.models.schemas import State
from app.agents import (
    classifier_node,
    planner_node,
    search_coordinator_node,
    router_node,
    parser_node,
    selector_node,
    comparator_node,
    reporter_node
)
from .conditions import should_start_planning, should_continue_search


def create_graph():
    """Create and compile the agent graph"""
    workflow = StateGraph(State)

    # Add all agent nodes
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("search_coordinator", search_coordinator_node)
    workflow.add_node("router", router_node)
    workflow.add_node("parser", parser_node)
    workflow.add_node("selector", selector_node)
    workflow.add_node("comparator", comparator_node)
    workflow.add_node("reporter", reporter_node)

    # Set entry point
    workflow.set_entry_point("classifier")

    # Add conditional edges from classifier
    workflow.add_conditional_edges(
        "classifier",
        should_start_planning,
        {
            "planner": "planner",
            "reporter": "reporter"
        }
    )

    # Add edge from planner to search coordinator
    workflow.add_edge("planner", "search_coordinator")

    # Add conditional edges from search coordinator
    workflow.add_conditional_edges(
        "search_coordinator",
        should_continue_search,
        {
            "router": "router",
            "comparator": "comparator",
            "reporter": "reporter"
        }
    )

    # Add processing chain
    workflow.add_edge("router", "parser")
    workflow.add_edge("parser", "selector")
    workflow.add_edge("selector", "search_coordinator")
    workflow.add_edge("comparator", "search_coordinator")

    # Add final edge to end
    workflow.add_edge("reporter", END)

    return workflow.compile()