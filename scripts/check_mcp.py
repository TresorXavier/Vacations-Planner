import asyncio

from app.mcp_tools.provider import MCPToolProvider, build_server_config


async def main():
    tools = await MCPToolProvider(build_server_config()).load()
    for t in tools:
        print(t.name, "-", t.description)

    weather = next(t for t in tools if t.name == "get_weather")
    route = next(t for t in tools if t.name == "find_places_or_route")

    print(await weather.ainvoke({"city": "Zanzibar, Tanzania"}))
    print(await weather.ainvoke({"city": "Nowhereville123"}))
    print(await route.ainvoke({"origin": "Stone Town, Zanzibar", "destination": "Nungwi, Zanzibar"}))


asyncio.run(main())