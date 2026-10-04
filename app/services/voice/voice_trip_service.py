import logging

from fastapi import HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.trips import TripReq
from app.services.trips import create_trip
from app.services.voice.trip_extractor import TripExtractor
from app.services.voice.voice_service import VoiceService

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ("destination", "days", "budget", "trip_style")


class VoiceTripService:
    def __init__(self, voice: VoiceService, extractor: TripExtractor, db: AsyncSession, user_id):
        self.voice = voice
        self.extractor = extractor
        self.db = db
        self.user_id = user_id

    async def create_trip_from_audio(self, file: UploadFile):
        transcript = await self.voice.speech_to_text(file)
        logger.info("Voice transcript: %s", transcript)

        draft = await self.extractor.extract(transcript)

        missing = [f for f in REQUIRED_FIELDS if getattr(draft, f) is None]
        if missing:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Please mention the missing details", "missing_fields": missing},
            )

        try:
            trip_data = TripReq(**draft.model_dump())
        except ValidationError as e:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Some trip details are invalid", "errors": e.errors(include_url=False)},
            )

        return await create_trip(trip_data, self.user_id, self.db)