# app/services/voice/voice_service.py
from fastapi import HTTPException, UploadFile, status

from app.services.voice.base import SpeechToText, TranscriptionError

ALLOWED_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/webm", "audio/mp4", "audio/m4a", "audio/ogg",
}


class VoiceService:
    def __init__(self, stt: SpeechToText, max_audio_mb: int):
        self.stt = stt
        self.max_bytes = max_audio_mb * 1024 * 1024

    async def speech_to_text(self, file: UploadFile) -> str:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported audio type")

        audio = await file.read(self.max_bytes + 1)      
        if len(audio) > self.max_bytes:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Audio file too large")
        if not audio:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty audio file")

        try:
            text = await self.stt.transcribe(audio, file.filename or "audio", file.content_type)
        except TranscriptionError:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not transcribe the audio")

        if not text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No speech detected")
        return text