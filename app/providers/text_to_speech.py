from pathlib import Path
from typing import Protocol


class TextToSpeechError(Exception):
    """Erro permanente retornado por um provedor de voz."""


class TransientTextToSpeechError(TextToSpeechError):
    """Erro que pode ser resolvido repetindo a mesma requisição."""


class TextToSpeechProvider(Protocol):
    name: str
    audio_extension: str

    def synthesize(self, *, text: str, output_path: Path) -> None:
        """Sintetiza ``text`` e grava o áudio em ``output_path``."""
