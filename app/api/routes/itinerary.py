import json
import uuid
from http import HTTPStatus

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes_deps import get_current_user
from app.core.lifespan_db import create_session
from app.models.users import Users
from app.schemas.itinerary import ItineraryReq
from app.services.itinerary import get_itinerary_by_trip,stream_itinerary

router = APIRouter(prefix="/itineraries", tags=["itineraries"])
async def serversentevents_wrapper(event_generator):
    """Format each yielded {"event": ..., "data": ...} dict as a properServer-Sent Event. """
    async for item in event_generator:
        event_name = item["event"]
        data = json.dumps(item["data"])
        yield f"event: {event_name}\ndata: {data}\n\n"
    
@router.post("",status_code=HTTPStatus.CREATED)
async def create_itinerary_route( body: ItineraryReq,user=Depends(get_current_user),
    db: AsyncSession = Depends(create_session)):
    
    return StreamingResponse(serversentevents_wrapper(stream_itinerary(body.trip_id,user.id,db)),
        media_type="text/event-stream"
    )

@router.get("/{trip_id}", status_code=HTTPStatus.OK)
async def get_by_trip(trip_id: uuid.UUID, current_user: Users = Depends(get_current_user),db: AsyncSession = Depends(create_session)):
    return await get_itinerary_by_trip( trip_id=trip_id,user_id=current_user.id,db=db)