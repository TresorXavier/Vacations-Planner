from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes_deps import get_current_user, get_trip_extractor, get_voice_service
from app.core.lifespan_db import create_session
from app.services.voice.trip_extractor import TripExtractor
from app.services.voice.voice_service import VoiceService
from app.services.voice.voice_trip_service import VoiceTripService

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/trip", status_code=status.HTTP_201_CREATED)
async def create_trip_from_voice(
    audio: UploadFile = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(create_session),
    voice: VoiceService = Depends(get_voice_service),
    extractor: TripExtractor = Depends(get_trip_extractor),
):
    return await VoiceTripService(voice, extractor, db, user.id).create_trip_from_audio(audio)