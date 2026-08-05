import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class MediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_assets"

    video_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("video_scenes.id", ondelete="SET NULL"), index=True
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(100))
    uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    license: Mapped[str | None] = mapped_column(String(255))
    prompt: Mapped[str | None] = mapped_column(Text)
    asset_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)

    video_project: Mapped["VideoProject"] = relationship(  # noqa: F821
        back_populates="media_assets"
    )
    video_scene: Mapped["VideoScene | None"] = relationship(  # noqa: F821
        back_populates="media_assets"
    )
