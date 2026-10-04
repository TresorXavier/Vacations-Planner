import json
import logging
import uuid

from fastapi import HTTPException, status
from langchain_core.messages import AIMessageChunk, ToolMessage
from pydantic import ValidationError                       # pydantic, not jsonschema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.travel_agent import TravelAgent
from app.models.itinerary import Itineraries
from app.models.trips import Trips
from app.schemas.itinerary import ItineraryContent
from app.utils.llm_output import extract_json_content, extract_text

logger = logging.getLogger(__name__)

ITINERARY_PROMPT = (
    "Create a complete travel itinerary for my trip with trip ID {trip_id}. "
    "Use my trip details and retrieve useful travel information, weather, "
    "maps, and pricing.\n\n"
    "Your FINAL answer must be ONLY one JSON object that follows this JSON schema exactly. "
    "Use no extra fields and no text outside the JSON:\n{schema}"
)
ITINERARY_SCHEMA = json.dumps(ItineraryContent.model_json_schema())

class ItineraryService:
    def __init__(self, agent: TravelAgent, db: AsyncSession):
        self.agent = agent
        self.db = db

    async def stream(self, trip_id: uuid.UUID, user_id: uuid.UUID):
        """Run the agent and yield SSE events."""
        if await self._get_trip(trip_id, user_id) is None:
            yield {"event": "error", "data": {"detail": "Trip not found"}}
            return

        final_text = ""
        announced_tools: set[str] = set()

        try:
            async for chunk, _meta in self.agent.stream(
                ITINERARY_PROMPT.format(trip_id=trip_id, schema=ITINERARY_SCHEMA),
                user_id=user_id,
                db=self.db,
                new_id=f"{trip_id}:{uuid.uuid4()}",
            ):
                for event in self._chunk_to_events(chunk, announced_tools):
                    if event["event"] == "message_chunk":
                        final_text += event["data"]["text"]
                    yield event
        except Exception:
            logger.exception("Agent stream failed for trip %s", trip_id)
            yield {"event": "error", "data": {"detail": "Itinerary generation failed"}}
            return

        async for event in self._finalize(trip_id, final_text):
            yield event

    async def get_by_trip(self, trip_id: uuid.UUID, user_id: uuid.UUID) -> Itineraries:
        """Return the saved itinerary of a trip, or raise 404."""
        if await self._get_trip(trip_id, user_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Trip not found")

        itinerary = await self._get_itinerary(trip_id)
        if itinerary is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
        return itinerary


    @staticmethod
    def _chunk_to_events(chunk, announced_tools: set[str]) -> list[dict]:
        """Convert one LangGraph chunk into zero or more SSE events."""
        events = []

        if isinstance(chunk, AIMessageChunk):
            for call in chunk.tool_calls or []:
                name = call.get("name")
                if name and name not in announced_tools:
                    announced_tools.add(name)
                    events.append({"event": "tool_started", "data": {"tool": name}})

            text = extract_text(chunk.content)
            if text:
                events.append({"event": "message_chunk", "data": {"text": text}})

        elif isinstance(chunk, ToolMessage):
            events.append({
                "event": "tool_result",
                "data": {
                    "tool": chunk.name,
                    "result_preview": (extract_text(chunk.content) or str(chunk.content))[:200],
                },
            })

        return events


    async def _finalize(self, trip_id: uuid.UUID, final_text: str):
        if not final_text.strip():
            yield {"event": "error", "data": {"detail": "Model returned no content"}}
            return

        try:
            raw_content = extract_json_content(final_text)
            validated = ItineraryContent.model_validate(raw_content)
        except ValueError as e:               
            logger.error("Invalid itinerary payload from model: %s", e)
            yield {"event": "error", "data": {"detail": "Model returned an invalid itinerary"}}
            return
        except ValidationError as e:          
            logger.error("Itinerary failed schema validation: %s", e)
            yield {"event": "error", "data": {"detail": "Model returned an incomplete or malformed itinerary"}}
            return

        content = validated.model_dump(mode="json")

        try:
            saved = await self._save(trip_id, content)
        except Exception:
            logger.exception("Could not save itinerary for trip %s", trip_id)
            yield {"event": "error", "data": {"detail": "Could not save the itinerary"}}
            return

        logger.info("Itinerary saved for trip %s", trip_id)
        yield {
            "event": "finished",
            "data": {"itinerary_id": str(saved.id), "trip_id": str(trip_id), **content},
        }

    
    async def _get_trip(self, trip_id: uuid.UUID, user_id: uuid.UUID) -> Trips | None:
        result = await self.db.execute(
            select(Trips).where(Trips.id == trip_id, Trips.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_itinerary(self, trip_id: uuid.UUID) -> Itineraries | None:
        result = await self.db.execute(
            select(Itineraries).where(Itineraries.trip_id == trip_id)
        )
        return result.scalar_one_or_none()

    async def _save(self, trip_id: uuid.UUID, content: dict) -> Itineraries:
        """Create the itinerary, or update it if one already exists."""
        itinerary = await self._get_itinerary(trip_id)

        if itinerary:
            itinerary.days = content
        else:
            itinerary = Itineraries(trip_id=trip_id, days=content)
            self.db.add(itinerary)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(itinerary)
        return itinerary