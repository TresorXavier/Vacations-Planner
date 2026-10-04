from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


class TripDraft(BaseModel):
    destination: str | None = Field(None, description="City or country to visit")
    days: int | None = Field(None, description="Number of days of the trip")
    budget: float | None = Field(
        None,
        description="Budget as a plain number, e.g. 1500. "
                    "Return null if the user gave no amount (words like 'medium' or 'cheap' are NOT an amount).",
    )
    trip_style: str | None = Field(None, description="Style, e.g. relaxed, adventure, family")

SYSTEM_PROMPT = (
    "Extract trip details from the user's spoken request. "
    "Use ONLY what the user said. If a detail is not mentioned, return null. "
    "Never guess or invent values. "
    "For budget, return a number only if the user said an amount."
)


class TripExtractor:
    def __init__(self, model_name: str, api_key: str):
        llm = ChatAnthropic(model=model_name, api_key=api_key)
        self._llm = llm.with_structured_output(TripDraft)

    async def extract(self, transcript: str) -> TripDraft:
        return await self._llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=transcript),
        ])