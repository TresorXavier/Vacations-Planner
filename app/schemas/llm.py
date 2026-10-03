from app.schemas.itinerary import ItineraryContent


itineraries_output_schema = {
    "format": {
        "type": "json_schema",
        "schema": ItineraryContent.model_json_schema(),
    }
}
weather_tool_schema = {
    "name": "get_weather",
    "description": (
        "Look up current weather conditions for a city, to help tailor "
        "itinerary recommendations (e.g. outdoor vs indoor activities)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name, e.g. 'Kigali'"}
        },
        "required": ["city"],
        "additionalProperties": False
    },
    "strict": True,
}

rag_tool_schema = {
    "name": "search_travel_knowledge",
    "description": (
        "Search the travel knowledge base for relevant information "
        "about destinations, attractions, activities, travel advice, "
        "and other travel-related topics."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The travel-related question or information to search for."
            }
        },
        "required": ["query"],
    },
}

pricing_tool_schema = {
    "name": "estimate_travel_cost",
    "description": (
        "Estimate the cost of a trip based on destination, "
        "duration, number of travelers, and travel preferences."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "The destination of the trip."
            },
            "duration_days": {
                "type": "integer",
                "description": "Number of days of the trip."
            },
            "travelers": {
                "type": "integer",
                "description": "Number of travelers."
            },
            "budget_level": {
                "type": "string",
                "enum": [
                    "budget",
                    "mid_range",
                    "luxury"
                ],
                "description": "The desired travel budget level."
            },
        },
        "required": [
            "destination",
            "duration_days",
            "travelers",
            "budget_level"
        ],
        "additionalProperties": False,
    },
    "strict": True,
}

maps_tool_schema = {
    "name": "find_places_or_route",
    "description": (
        "Find places, attractions, or routes between locations. "
        "Use this when the user asks for places to visit, "
        "distances, directions, or travel routes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "The starting location."
            },
            "destination": {
                "type": "string",
                "description": "The destination or place to find."
            },
            "request_type": {
                "type": "string",
                "enum": [
                    "route",
                    "distance",
                    "places"
                ],
                "description": "The type of maps information requested."
            },
        },
        "required": ["destination", "request_type"],
        "additionalProperties": False,
    },
    "strict": True,
}