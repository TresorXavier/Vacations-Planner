from mcp.server.fastmcp import FastMCP
import asyncio
from app.tools.maps import find_places_or_route
from app.tools.weather import get_weather

mcp = FastMCP("travel-tools")



@mcp.tool(name="get_weather")
async def get_weather_tool(city: str) -> str:
    """Get the weather forecast for a city. Use only the city name, for example 'Zanzibar'."""
    result = await asyncio.to_thread(get_weather, city)
    return str(result)


@mcp.tool(name="find_places_or_route")
async def get_route(origin: str, destination: str) -> str:
    """Get the driving distance and estimated travel time between two locations."""
    return await asyncio.to_thread(find_places_or_route, origin, destination)



if __name__ == "__main__":
    mcp.run(transport="stdio")