import uuid
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from app.services.trips import get_trip_by_id


class TripDetailsInput(BaseModel):
    trip_id: str = Field(description="The UUID of the trip to retrieve details for.")


@tool("get_trip_details", args_schema=TripDetailsInput)
async def get_trip_details(trip_id: str, config: RunnableConfig) -> str:
    """Retrieve the destination, duration, budget, and style for a given trip_id."""
    user_id = uuid.UUID(config["configurable"]["user_id"])
    db = config["configurable"]["db"]

    try:
        trip = await get_trip_by_id(trip_id, user_id, db)
    except Exception as e:
        return f"Could not retrieve trip {trip_id}: {e}"

    return (
        f"destination: {trip.destination}, "
        f"days: {trip.days}, budget: {trip.budget}, "
        f"style: {trip.trip_style}"
    )