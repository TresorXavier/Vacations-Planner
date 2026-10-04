from abc import ABC, abstractmethod

class SpeechSynthesisError(Exception):
    """The text-to-speech engine failed."""

class TextToSpeech(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Return MP3 audio of the text."""