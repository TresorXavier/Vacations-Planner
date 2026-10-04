import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.llm_output import extract_text

SCRIPT_PROMPT = (
    "You turn a travel itinerary (JSON) into a short script that will be read aloud. "
    "Rules: 120 to 200 words, friendly and natural, plain sentences. "
    "Mention the destination, then one highlight per day, then one tip about weather or budget. "
    "No lists, no markdown, no emojis, no links, no JSON keys, no special symbols. "
    "Use only facts present in the itinerary."
)


class SpeechScriptWriter:
    def __init__(self, model_name: str, api_key: str):
        self._llm = ChatAnthropic(model=model_name, api_key=api_key)

    async def write(self, itinerary_content: dict) -> str:
        response = await self._llm.ainvoke([
            SystemMessage(content=SCRIPT_PROMPT),
            HumanMessage(content=json.dumps(itinerary_content, ensure_ascii=False)),
        ])
        return extract_text(response.content).strip()