from langchain_core.tools import StructuredTool
from app.schemas.map import MapsInput
from app.core.config import settings
import requests



def find_places_or_route(origin: str,destination: str) -> str:
    """Get the driving distance and estimated travel time between two locations."""

    def geocode(place: str):
        response = requests.get(
            settings.NOMINATIM_URL,
            params={"q": place,"format": "json","limit": 1},
            headers={"User-Agent": "VacationPlanner/1.0"},
            timeout=10
        )
        results = response.json()

        if not results:
            return None

        return float(results[0]["lat"]), float(results[0]["lon"])

    origin_coords = geocode(origin)
    destination_coords = geocode(destination)

    if not origin_coords or not destination_coords:
        return "Could not find one of the locations."

    coordinates = (
        f"{origin_coords[1]},{origin_coords[0]};"
        f"{destination_coords[1]},{destination_coords[0]}"
    )

    response = requests.get(f"{settings.OSRM_URL}/{coordinates}",params={"overview": "false"},timeout=10)
    data = response.json()

    if data.get("code") != "Ok":
        return "Could not find a route."

    route = data["routes"][0]

    distance_km = route["distance"] / 1000
    duration_minutes = route["duration"] / 60

    return (
        f"Route from {origin} to {destination}: "
        f"{distance_km:.1f} km, approximately "
        f"{duration_minutes:.0f} minutes by car."
    )


maps_tool = StructuredTool.from_function(
    func=find_places_or_route,
    name="find_places_or_route",
    description=("Get the driving distance and estimated travel time between two locations."),
    args_schema=MapsInput
)