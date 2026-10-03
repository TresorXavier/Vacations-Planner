
import uuid
from typing import AsyncIterator, TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class TravelAgent:
    """Compiled once at startup, reused for every request."""

    def __init__(self, tools: list, checkpointer, model_name: str, api_key: str, system_prompt: str):
        self._tools = tools
        self._system_prompt = system_prompt
        self._llm = ChatAnthropic(model=model_name, api_key=api_key).bind_tools(tools)
        self._graph = self._build_graph(checkpointer)

  
    def _build_graph(self, checkpointer):
        graph = StateGraph(AgentState)
        graph.add_node("agent", self._call_model)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_edge(START, "agent")
        graph.add_conditional_edges(
            "agent", self._route, {"continue": "tools", "end": END}
        )
        graph.add_edge("tools", "agent")
        return graph.compile(checkpointer=checkpointer)

    async def _call_model(self, state: AgentState) -> dict:
        messages = [SystemMessage(content=self._system_prompt)] + list(state["messages"])
        response = await self._llm.ainvoke(messages)
        return {"messages": [response]}

    @staticmethod
    def _route(state: AgentState) -> str:
        return "continue" if state["messages"][-1].tool_calls else "end"

    async def stream(self, user_message: str, *, user_id: uuid.UUID, db, new_id: str) -> AsyncIterator[tuple]:
        """Yields (chunk, metadata) from the graph."""
        config = {
            "configurable": {
                "thread_id": new_id,          
                "user_id": str(user_id),
                "db": db,
            }
        }
        async for item in self._graph.astream(
            {"messages": [HumanMessage(content=user_message)]},
            stream_mode="messages",
            config=config,
        ):
            yield item
