import json
import logging
from fastapi import HTTPException
from pydantic import ValidationError
from langchain_core.messages import HumanMessage
from app.schemas.itinerary import ItineraryContent
from app.schemas.llm import itineraries_output_schema
from app.utils.prompt_registry import load_prompt_name
from app.agents.travel_agent import agent_graph

logger = logging.getLogger(__name__)
itinerary_prompt = load_prompt_name("itinerary_generation", version=2).template
def build_itineraries(destination, days, budget, travel_style):

    prompt = itinerary_prompt.format(
        destination=destination,
        days=days,
        budget=budget,
        travel_style=travel_style,
        output_schema=json.dumps(itineraries_output_schema["format"]["schema"], indent=2),
    )

    result = agent_graph.invoke({"messages": [HumanMessage(content=prompt)]})
    final_message = result["messages"][-1]

    logger.info(
        "Agent run complete | messages=%d | final_message_type=%s",
        len(result["messages"]), type(final_message).__name__,
    )

    raw = final_message.content

    try:
        content = ItineraryContent.model_validate_json(raw)
    except ValidationError as e:
        logger.error("Invalid itinerary payload from model: %s", e)
        raise HTTPException(status_code=502, detail="Model returned an invalid itinerary")

    return content