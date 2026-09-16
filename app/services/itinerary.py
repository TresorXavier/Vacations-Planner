import json
import logging
import re
import uuid

from fastapi import HTTPException, status
from jsonschema import ValidationError
from langchain_core.messages import HumanMessage, AIMessageChunk, ToolMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import lifespan_db
from app.agents.travel_agent import build_agent_graph
from app.models.itinerary import Itineraries
from app.models.trips import Trips
from app.schemas.itinerary import ItineraryContent

logger = logging.getLogger(__name__)


def extract_json_content(raw: str) -> dict:
    """
        Extract the itinerary JSON from the model's response.
        The extraction follows these steps:
        1. First, look for a JSON block wrapped in ```json ... ```.
        2. If none is found, look for the outermost JSON object enclosed by { and }.
        3. If that also fails, try parsing the entire cleaned response as JSON.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        braced = re.search(r"(\{.*\})", raw, re.DOTALL)
        candidate = braced.group(1) if braced else raw.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse model output as JSON: {e}\nExtracted: {candidate[:500]!r}"
        )


def extract_text(content) -> str:
 
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)

    return ""


async def stream_itinerary(trip_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(Trips).where(Trips.id == trip_id, Trips.user_id == user_id)
    )
    trip = result.scalar_one_or_none()

    if trip is None:
        yield {"event": "error", "data": {"detail": "Trip not found"}}
        return

    agent_graph = build_agent_graph(user_id=user_id, db=db,checkpointer=lifespan_db.checkpointer)

    final_text = ""
    announced_tools = set()

    try:
        config = {"configurable": {"thread_id": str(trip_id)}}
        async for chunk, metadata in agent_graph.astream(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            f"Create a complete travel itinerary for my trip "
                            f"with trip ID {trip_id}. Use my trip details and "
                            f"retrieve useful travel information, weather, "
                            f"maps, and pricing."
                        )
                    )
                ]
            },
            stream_mode="messages",
            config=config,
        ):
            if isinstance(chunk, AIMessageChunk):

                for call in (chunk.tool_calls or []):
                    name = call.get("name")
                    if not name or name in announced_tools:
                        continue
                    announced_tools.add(name)
                    yield {"event": "tool_started", "data": {"tool": name}}

                text_piece = extract_text(chunk.content)
                if text_piece:
                    final_text += text_piece
                    yield {"event": "message_chunk", "data": {"text": text_piece}}

            elif isinstance(chunk, ToolMessage):
                yield {
                    "event": "tool_result",
                    "data": {
                        "tool": chunk.name,
                        "result_preview": str(chunk.content)[:200],
                    },
                }

    except Exception as e:
        logger.exception("Agent stream failed for trip %s", trip_id)
        yield {"event": "error", "data": {"detail": str(e)}}
        return

    if not final_text.strip():
        yield {"event": "error", "data": {"detail": "Model returned no content"}}
        return

    try:
        itinerary_content = extract_json_content(final_text)
    except ValueError as e:
        logger.error("Invalid itinerary payload from model: %s", e)
        yield {"event": "error", "data": {"detail": "Model returned an invalid itinerary"}}
        return

    try:
        validated = ItineraryContent.model_validate(itinerary_content)
    except ValidationError as e:
        logger.error("Itinerary JSON parsed but failed schema validation: %s", e)
        yield {"event": "error", "data": {"detail": "Model returned an incomplete or malformed itinerary"}}
        return

    existing = await db.execute(select(Itineraries).where(Itineraries.trip_id == trip_id))
    existing_itinerary = existing.scalar_one_or_none()
    

    if existing_itinerary:
        existing_itinerary.days = itinerary_content
        await db.commit()
        await db.refresh(existing_itinerary)
        saved = existing_itinerary
    else:
        saved = Itineraries(trip_id=trip_id, days=itinerary_content)
        db.add(saved)
        await db.commit()
        await db.refresh(saved)

    logger.info("Itinerary saved for trip %s", trip_id)

    yield {
        "event": "finished",
        "data": {
            "itinerary_id": str(saved.id),
            "trip_id": str(trip_id),
            **validated.model_dump()
        }
    }


async def get_itinerary_by_trip(trip_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(Trips).where(Trips.id == trip_id, Trips.user_id == user_id)
    )

    trip = result.scalar_one_or_none()

    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Trip not found")

    result = await db.execute(select(Itineraries).where(Itineraries.trip_id == trip_id))
    itinerary = result.scalar_one_or_none()

    if itinerary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found",
        )

    return itinerary