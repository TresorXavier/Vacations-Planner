import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.itinerary_builder import build_itineraries
from app.models.trips import Trips
from app.models.itinerary import Itineraries
from fastapi import HTTPException, status

from app.schemas.itinerary import ItineraryRes

logger = logging.getLogger(__name__)


async def create_itinerary(tripId: uuid.UUID, user_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(Trips).where(Trips.id == tripId, Trips.user_id == user_id)
    )
    trip = result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    itinerary_content = build_itineraries(
        destination=trip.destination,
        days=trip.days,
        budget=trip.budget,
        travel_style=trip.trip_style
    )
    itinerary_days = ItineraryRes(trip_id=trip.id, **itinerary_content.model_dump())

    itinerary = await db.execute(select(Itineraries).where(Itineraries.trip_id == tripId))
    existing_itinerary = itinerary.scalar_one_or_none()

    days_data = [d.model_dump(mode="json") for d in itinerary_days.itinerary]

    if existing_itinerary:
        existing_itinerary.days = days_data
        await db.commit()
        await db.refresh(existing_itinerary)
        return itinerary_days

    new_itinerary = Itineraries(trip_id=tripId, days=days_data)
    db.add(new_itinerary)
    await db.commit()
    await db.refresh(new_itinerary)
    return itinerary_days

async def get_itinerary_by_trip(trip_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession):
    trips = await db.execute(
        select(Trips).where(Trips.id == trip_id, Trips.user_id == user_id)
    )
    if not trips.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    result = await db.execute(
        select(Itineraries).where(Itineraries.trip_id == trip_id)
    )
    return result.scalars().all()
