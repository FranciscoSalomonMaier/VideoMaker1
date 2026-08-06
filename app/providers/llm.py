from typing import Protocol, TypeVar

from pydantic import BaseModel

StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)


class LLMProvider(Protocol):
    """Porta para provedores de LLM com saída estruturada."""

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredResponse],
    ) -> StructuredResponse: ...
