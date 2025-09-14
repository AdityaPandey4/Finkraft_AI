
from typing import TypedDict, List, Optional
import pandas as pd
from langgraph.graph import StateGraph, END
from .nodes import classify_query, code_generation, code_execution, suggestion, insight_generation

class AgentState(TypedDict):
    data_id: str
    dataframe: Optional[pd.DataFrame]
    query: str
    chat_history: List[str]
    explanation: Optional[str]
    charts: Optional[List[dict]]
    suggestions: Optional[List[dict]]
    error: Optional[str]
    insight: Optional[dict]
    classification: str
    code: Optional[str]

workflow = StateGraph(AgentState)

workflow.add_node("classify_query", classify_query)
workflow.add_node("code_generation", code_generation)
workflow.add_node("code_execution", code_execution)
workflow.add_node("suggestion", suggestion)
workflow.add_node("insight_generation", insight_generation)

workflow.set_entry_point("classify_query")

workflow.add_conditional_edges(
    "classify_query",
    lambda state: state["classification"],
    {
        "code_generation": "code_generation",
        "suggestion": "suggestion",
        "greeting": END,
    },
)

workflow.add_edge("code_generation", "code_execution")

workflow.add_conditional_edges(
    "code_execution",
    lambda state: "retry" if state.get("error") else "proceed",
    {
        "retry": "code_generation",
        "proceed": "insight_generation",
    },
)

workflow.add_edge("suggestion", END)
workflow.add_edge("insight_generation", END)

app = workflow.compile()
