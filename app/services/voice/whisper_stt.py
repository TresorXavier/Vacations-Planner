import asyncio
import io
import logging
from faster_whisper import WhisperModel
from app.services.voice.base import SpeechToText, TranscriptionError
from app.core.config import settings

logger = logging.getLogger(__name__)

class FasterWhisperTranscriber(SpeechToText):
    def __init__(self, model_size: str):
        self._model = WhisperModel(settings.STT_MODEL_SIZE, device="cpu", compute_type="int8")

    def _transcribe_sync(self, audio: bytes) -> str:
        segments, _ = self._model.transcribe(io.BytesIO(audio), vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()

    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> str:
        try:
            return await asyncio.to_thread(self._transcribe_sync, audio)
        except Exception as e:
            logger.exception("Transcription failed")
            raise TranscriptionError("Speech engine failed") from e