import asyncio
import io
import logging
from gtts import gTTS
from app.services.voice.tts_base import SpeechSynthesisError, TextToSpeech

logger = logging.getLogger(__name__)


class GTTSEngine(TextToSpeech):
    def __init__(self, lang: str):
        self._lang = lang

    def _synthesize_sync(self, text: str) -> bytes:
        buffer = io.BytesIO()
        gTTS(text=text, lang=self._lang).write_to_fp(buffer)
        return buffer.getvalue()

    async def synthesize(self, text: str) -> bytes:
        try:
            audio = await asyncio.to_thread(self._synthesize_sync, text)
        except Exception as e:
            logger.exception("Speech synthesis failed")
            raise SpeechSynthesisError("Speech engine failed") from e

        if not audio:
            raise SpeechSynthesisError("Speech engine returned no audio")
        return audio