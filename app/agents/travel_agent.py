from typing import TypedDict, Annotated, Sequence

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.utils.prompt_registry import load_prompt_name

from app.tools.rag_tools import rag_tool
from app.tools.weather import weather_tool
from app.tools.maps import maps_tool
from app.tools.pricing import cost_calculation
from app.tools.trip_details_tool import build_trip_details_tool


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def build_agent_graph(user_id, db,checkpointer):
    """
    Build and compile a travel-planning agent graph.
    user_id and db are application-controlled values used by
    the trip-details tool to retrieve the authenticated user's trip.
    """

    trip_details_tool = build_trip_details_tool(user_id=user_id,db=db)

    tools = [
        rag_tool,
        weather_tool,
        maps_tool,
        cost_calculation,
        trip_details_tool,
    ]

    llm = ChatAnthropic(model=settings.MODEL_NAME,api_key=settings.ANTHROPIC_API_KEY).bind_tools(tools)

    def model_call(state: AgentState) -> AgentState:
        """
        Ask the LLM what to do next. The LLM can either:
        - answer the user directly
        - request one or more tools
        """

        system_prompt = load_prompt_name("travel_planner_system",version=2).template
        messages = messages = [SystemMessage(content=system_prompt)] + state["messages"]

        response = llm.invoke(messages)

        return {"messages": [response]}


    def should_continue_call_tools(state: AgentState) -> str:
        """
        Decide what should happen after the agent responds.
        If the LLM requested tools go to ToolNode Otherwise finish the graph
        """

        last_message = state["messages"][-1]

        if last_message.tool_calls:
            return "continue"

        return "end"


    graph = StateGraph(AgentState)

    graph.add_node("agent",model_call)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START,"agent")

    graph.add_conditional_edges(
        "agent",
        should_continue_call_tools,
        {
            "continue": "tools",
            "end": END,
        },
    )
    graph.add_edge("tools","agent",)

    return graph.compile(checkpointer=checkpointer)
