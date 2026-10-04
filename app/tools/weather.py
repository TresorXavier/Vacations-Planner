import logging
import requests
from langchain_core.tools import StructuredTool
from app.core.config import settings
from app.schemas.weather import WeatherInput, WeatherResponse

logger = logging.getLogger(__name__)

def get_weather(city: str) -> WeatherResponse | str:
    name = city.split(",")[0].strip()

    try:
        geo = requests.get(settings.GEOCODING_URL, params={"name": name, "count": 1}, timeout=10)
        geo.raise_for_status()

        results = geo.json().get("results")
        if not results:
            return f"Could not find a location named '{name}'. Try only the city name."
        location = results[0]

        forecast = requests.get(
            settings.FORECAST_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "temperature_2m,weather_code,wind_speed_10m",
            },
            timeout=10,
        )
        forecast.raise_for_status()
        current = forecast.json()["current"]

    except (requests.RequestException, KeyError, ValueError):
        logger.exception("Weather lookup failed for %r", city)
        return "The weather service is unavailable right now."

    return WeatherResponse(
        city=location["name"],
        country=location.get("country", ""),
        temperature=current["temperature_2m"],
        wind_speed=current["wind_speed_10m"],
        weather_code=current["weather_code"],
    )


weather_tool = StructuredTool.from_function(
    func=get_weather,
    name="get_weather",
    description=(
        "Look up current weather conditions for a city, to help tailor "
        "itinerary recommendations (e.g. outdoor vs indoor activities). "
        "Use only the city name, for example 'Zanzibar'."
    ),
    args_schema=WeatherInput,
)