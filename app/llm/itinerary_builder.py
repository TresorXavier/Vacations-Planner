import json
import logging

from fastapi import HTTPException
from pydantic import ValidationError

from app.llm.client import run_tools
from app.schemas.itinerary import ItineraryContent
from app.schemas.llm import itineraries_output_schema, weather_tool_schema
from app.utils.prompt_registry import load_prompt_name
from app.rag.retriever import retrieve_trip_context, format_context_for_prompt


itinerary_prompt = load_prompt_name("itinerary_generation", version=2).template
system_prompt = load_prompt_name("travel_planner_system", version=2).template

logger = logging.getLogger(__name__)
def build_itineraries(destination, days, budget, travel_style):
  
    retrieval_result = retrieve_trip_context(destination, travel_style)

    logger.info(
        "RAG retrieval | destination=%r | matched=%r | country=%r | fallback=%s | chunks=%d | files=%s",
        destination,
        retrieval_result["matched_destination"],
        retrieval_result["matched_country"],
        retrieval_result["used_fallback"],
        len(retrieval_result["chunks"]),
        [c["metadata"]["filename"] for c in retrieval_result["chunks"]],
    )

    context_block = format_context_for_prompt(retrieval_result)

    if retrieval_result["used_fallback"]:
        logger.warning(
            "No exact destination match for %r (country: %r), fell back to country-level context",
            destination, retrieval_result["matched_country"],
        )

    prompt = itinerary_prompt.format(
        destination=destination,
        days=days,
        budget=budget,
        travel_style=travel_style,
        context=context_block,
        output_schema=json.dumps(itineraries_output_schema["format"]["schema"], indent=2),
    )

    raw = run_tools(prompt, tools=[weather_tool_schema], system=system_prompt)

    try:
        content = ItineraryContent.model_validate_json(raw)
    except ValidationError as e:
        logger.error("Invalid itinerary payload from model: %s", e)
        raise HTTPException(status_code=502, detail="Model returned an invalid itinerary")

    return content
