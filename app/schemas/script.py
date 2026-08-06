from pydantic import BaseModel, Field


class GeneratedScene(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    narration: str = Field(min_length=1)
    visual_description: str | None = None
    duration_seconds: float | None = Field(default=None, gt=0)


class GeneratedScript(BaseModel):
    summary: str = Field(min_length=1)
    script: str = Field(min_length=1)
    scenes: list[GeneratedScene] = Field(min_length=1)
