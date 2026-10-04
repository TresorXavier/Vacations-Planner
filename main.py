import asyncio
import logging
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
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
from app.api.routes.voice import router as voice_router
from app.services.voice.trip_extractor import TripExtractor
from app.services.voice.whisper_stt import FasterWhisperTranscriber
from app.tools.trip_details_tool import get_trip_details
from app.tools.rag_tools import rag_tool
from app.tools.weather import weather_tool
from app.tools.maps import maps_tool
from app.tools.pricing import cost_calculation
from app.core.lifespan_db import database   
from fastapi import FastAPI, Request
from app.core.config import settings
from app.api.routes_deps import logging_middleware
from app.core.validation import Validation_Exeptions_Handler
from app.utils.prompt_registry import load_prompt_name  
from app.services.voice.gtts_engine import GTTSEngine 
from app.services.voice.speech_script_writer import SpeechScriptWriter
from app.mcp_tools.provider import MCPToolProvider, build_server_config



logging.basicConfig(level=logging.INFO,format="%(levelname)s | %(name)s | %(message)s")
       
        
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stt = await asyncio.to_thread(FasterWhisperTranscriber, settings.STT_MODEL_SIZE)
    app.state.trip_extractor = TripExtractor(settings.MODEL_NAME, settings.ANTHROPIC_API_KEY)
    app.state.script_writer = SpeechScriptWriter(settings.MODEL_NAME, settings.ANTHROPIC_API_KEY)
    app.state.tts = GTTSEngine(settings.TTS_LANG)
    await database.startup()
    
    try:
        mcp_tools = await MCPToolProvider(build_server_config()).load(
        allowed={"get_weather", "find_places_or_route"})
    except Exception:
        logging.getLogger(__name__).exception("MCP unavailable, using local tools")
        
        
    mcp_tools = [weather_tool, maps_tool]
    local_tools = [rag_tool, cost_calculation, get_trip_details]

    app.state.travel_agent = TravelAgent(
        tools=[*local_tools,*mcp_tools],
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

@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):
    logging.getLogger(__name__).exception("Database error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

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
app.include_router(voice_router)

if __name__ == "__main__":
    uvicorn.run("main:app",host="127.0.0.1",port=8080,reload=True)