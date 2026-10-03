import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from app.agents.travel_agent import TravelAgent
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as user_router
from app.api.routes.trips import router as trips_router
from app.api.routes.itinerary import router as itineraries_router
from app.tools.trip_details_tool import get_trip_details
from app.tools.rag_tools import rag_tool
from app.tools.weather import weather_tool
from app.tools.maps import maps_tool
from app.tools.pricing import cost_calculation
from app.core.lifespan_db import database   
from fastapi import FastAPI
from app.core.config import settings
from app.api.routes_deps import logging_middleware
from app.core.validation import Validation_Exeptions_Handler
from app.utils.prompt_registry import load_prompt_name   

logging.basicConfig(level=logging.INFO,format="%(levelname)s | %(name)s | %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.startup()

    app.state.travel_agent = TravelAgent(
        tools=[rag_tool, weather_tool, maps_tool, cost_calculation, get_trip_details],
        checkpointer=database.checkpointer,
        model_name=settings.MODEL_NAME,
        api_key=settings.ANTHROPIC_API_KEY,
        system_prompt=load_prompt_name("travel_planner_system", version=2).template,
    )
    yield
    await database.shutdown()

app = FastAPI(
    title="Vacation Planning",
    lifespan=lifespan,
    version="1.0",
    summary= """
    Vacation Planning is a backend REST API built with FastAPI that helps users
    organize and manage their trips efficiently.
    """)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError,Validation_Exeptions_Handler)
app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(trips_router)
app.include_router(itineraries_router)

if __name__ == "__main__":
    uvicorn.run("main:app",host="127.0.0.1",port=8080,reload=True)