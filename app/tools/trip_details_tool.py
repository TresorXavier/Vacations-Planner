from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from app.services.trips import get_trip_by_id


class TripDetailsInput(BaseModel):
    trip_id: str = Field(description="The UUID of the trip to retrieve details for.")


def build_trip_details_tool(user_id, db):
    """Builds a trip-details tool bound to a specific request'sdb session and user_id. """

    async def get_trip_details(trip_id: str) -> str:
        try:
            trip = await get_trip_by_id(trip_id, user_id, db)
        except Exception as e:
            return f"Could not retrieve trip {trip_id}: {e}"

        return (
            f"destination: {trip.destination}, "
            f"days: {trip.days}, budget: {trip.budget}, "
            f"style: {trip.trip_style}"
        )

    return StructuredTool.from_function(
        coroutine=get_trip_details, 
        name="get_trip_details",
        description="Retrieve the destination, duration, budget, and style for a given trip_id.",
        args_schema=TripDetailsInput,
    )