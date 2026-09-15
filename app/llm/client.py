from anthropic import Anthropic
from fastapi import HTTPException
from app.llm.message import add_assistant_message, add_user_message, text_from_message
from app.schemas.llm import itineraries_output_schema
from app.core.config import settings
from app.llm.use_tools import excecute_tools
from app.utils.prompt_registry import load_prompt_name
import logging

client = Anthropic( api_key=settings.ANTHROPIC_API_KEY)
logger = logging.getLogger(__name__)
model = settings.MODEL_NAME
max_token = settings.MAX_TOKEN
model = settings.MODEL_NAME
max_token = settings.MAX_TOKEN

system_prompt = load_prompt_name("travel_planner_system",version=2).template

def run_tools(user_prompt, tools=None, system=None):
    messages = []
    add_user_message(messages, user_prompt)

    params = {
        "model": model,
        "messages": messages,
        "max_tokens": max_token,
        "system": system or system_prompt,
        "output_config":itineraries_output_schema
    }
    if tools:
        params["tools"] = tools
    response = client.messages.create(**params)
    add_assistant_message(messages, response)

    while response.stop_reason == "tool_use":
        tools_result = [
            excecute_tools(block)
            for block in response.content
            if block.type == "tool_use"
        ]
        add_user_message(messages, tools_result)
        response = client.messages.create(**params)
        add_assistant_message(messages, response)
        
        if response.stop_reason == "refusal":
            raise HTTPException(status_code=422, detail="Model declined to generate this itinerary")
        if response.stop_reason == "max_tokens":
            raise HTTPException(status_code=422, 
                                detail="Itinerary generation exceeded the maximum output length. Try reducing the itinerary scope.")

    return text_from_message(response)
