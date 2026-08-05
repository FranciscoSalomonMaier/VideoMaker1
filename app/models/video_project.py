import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class VideoProjectStatus(StrEnum):
    DRAFT = "DRAFT"
    RESEARCHING = "RESEARCHING"
    SCRIPT_GENERATING = "SCRIPT_GENERATING"
    SCRIPT_READY = "SCRIPT_READY"
    AUDIO_GENERATING = "AUDIO_GENERATING"
    ASSETS_GENERATING = "ASSETS_GENERATING"
    RENDERING = "RENDERING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class VideoProject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "video_projects"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[VideoProjectStatus] = mapped_column(
        Enum(VideoProjectStatus, native_enum=False, length=32),
        default=VideoProjectStatus.DRAFT,
        nullable=False,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(Text)
    script: Mapped[str | None] = mapped_column(Text)

    topic: Mapped["Topic"] = relationship(back_populates="video_projects")  # noqa: F821
    scenes: Mapped[list["VideoScene"]] = relationship(  # noqa: F821
        back_populates="video_project", cascade="all, delete-orphan", order_by="VideoScene.position"
    )
    media_assets: Mapped[list["MediaAsset"]] = relationship(  # noqa: F821
        back_populates="video_project", cascade="all, delete-orphan"
    )
    publications: Mapped[list["Publication"]] = relationship(  # noqa: F821
        back_populates="video_project", cascade="all, delete-orphan"
    )
