from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import VideoProjectStatus


class VideoProjectCreate(BaseModel):
    topic_id: UUID
    language: str = Field(min_length=2, max_length=20)
    duration_minutes: int = Field(gt=0, le=180)
    format: str = Field(min_length=1, max_length=50)


class VideoProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    title: str
    language: str
    duration_minutes: int
    format: str
    status: VideoProjectStatus
    created_at: datetime
    updated_at: datetime
