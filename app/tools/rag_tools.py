from langchain_core.tools import StructuredTool
from app.rag.retriever import retrieve_trip_context, format_context_for_prompt
from app.schemas.rag import RAGInput


def search_travel_knowledge(destination: str, travel_style: str) -> str:
    """Search the travel knowledge base for a given destination and trip style."""
    
    try:
        result = retrieve_trip_context(destination, travel_style)
    except ValueError as e:

        return f"Could not search travel knowledge: {e}"

    return format_context_for_prompt(result)


rag_tool = StructuredTool.from_function(
    func=search_travel_knowledge,
    name="search_travel_knowledge",
    description=(
        "Search the travel knowledge base for information about a specific "
        "destination attractions, local tips, hidden gems, and travel "
        "advice. Requires a real destination name and a trip style."
    ),
    args_schema=RAGInput,
)