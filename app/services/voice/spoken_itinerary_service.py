import logging
import uuid

from fastapi import HTTPException, status

from app.services.itinerary import ItineraryService
from app.services.voice.speech_script_writer import SpeechScriptWriter
from app.services.voice.tts_base import SpeechSynthesisError, TextToSpeech

logger = logging.getLogger(__name__)


class SpokenItineraryService:
    def __init__(
        self,
        itineraries: ItineraryService,
        writer: SpeechScriptWriter,
        tts: TextToSpeech,
    ):
        self.itineraries = itineraries
        self.writer = writer
        self.tts = tts

    async def audio_for_trip(self, trip_id: uuid.UUID, user_id: uuid.UUID) -> bytes:
  
        itinerary = await self.itineraries.get_by_trip(trip_id, user_id)

        script = await self.writer.write(itinerary.days)
        if not script:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not prepare the spoken summary")
        logger.info("Spoken script for trip %s: %d characters", trip_id, len(script))

        try:
            return await self.tts.synthesize(script)
        except SpeechSynthesisError:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not generate the audio")