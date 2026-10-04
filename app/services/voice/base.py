from abc import ABC, abstractmethod


class TranscriptionError(Exception):
    """The speech provider failed."""


class SpeechToText(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> str:
        """Return the text spoken in the audio."""