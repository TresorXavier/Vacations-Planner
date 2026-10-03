
from langchain_core.tools import StructuredTool, tool
import requests
from app.schemas.weather import WeatherInput, WeatherResponse
    
def get_weather(city:WeatherInput)-> WeatherResponse:
    response =  requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name" :city,
            "count":1    
        }
    )
    
    response.raise_for_status()
    results =  response.json()["results"]
    
    location = results[0]
    
    weather = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": "temperature_2m,weather_code,wind_speed_10m"
        }
    )
    weather.raise_for_status()
    
    current = weather.json()["current"]
    return WeatherResponse(
        city= location["name"],
        country=location["country"],
        temperature=current["temperature_2m"],
        wind_speed=current["wind_speed_10m"],
        weather_code=current["weather_code"]
    )

weather_tool = StructuredTool.from_function(
    func=get_weather,
    name="get_weather",
    description=(
        "Look up current weather conditions for a city, to help tailor "
        "itinerary recommendations (e.g. outdoor vs indoor activities)."
    ),
    args_schema=WeatherInput,
)