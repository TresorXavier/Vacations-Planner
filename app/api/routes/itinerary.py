import json
import uuid
from http import HTTPStatus

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.travel_agent import TravelAgent
from app.api.routes_deps import get_current_user, get_spoken_itinerary_service, get_travel_agent
from app.core.lifespan_db import create_session
from app.models.users import Users
from app.schemas.itinerary import ItineraryReq
from app.services.itinerary import ItineraryService
from app.services.voice.spoken_itinerary_service import SpokenItineraryService

router = APIRouter(prefix="/itineraries", tags=["itineraries"])
async def serversentevents_wrapper(event_generator):
    """Format each yielded {"event": ..., "data": ...} dict as a properServer-Sent Event. """
    async for item in event_generator:
        event_name = item["event"]
        data = json.dumps(item["data"])
        yield f"event: {event_name}\ndata: {data}\n\n"
    
@router.post("", status_code=HTTPStatus.CREATED)
async def create_itinerary_route(
    body: ItineraryReq,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(create_session),
    agent: TravelAgent = Depends(get_travel_agent),
):
    service = ItineraryService(agent, db)
    return StreamingResponse(
        serversentevents_wrapper(service.stream(body.trip_id, user.id)),
        media_type="text/event-stream",
    )


@router.get("/{trip_id}", status_code=HTTPStatus.OK)
async def get_by_trip(
    trip_id: uuid.UUID,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(create_session),
    agent: TravelAgent = Depends(get_travel_agent),
):
    return await ItineraryService(agent, db).get_by_trip(trip_id, current_user.id)

@router.get("/{trip_id}/audio")
async def get_itinerary_audio(
    trip_id: uuid.UUID,
    user=Depends(get_current_user),
    service: SpokenItineraryService = Depends(get_spoken_itinerary_service),
):
    audio = await service.audio_for_trip(trip_id, user.id)
    return Response(content=audio, media_type="audio/mpeg")
