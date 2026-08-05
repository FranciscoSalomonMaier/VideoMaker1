import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class VideoScene(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "video_scenes"
    __table_args__ = (UniqueConstraint("video_project_id", "position", name="scene_position"),)

    video_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    visual_description: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    video_project: Mapped["VideoProject"] = relationship(back_populates="scenes")  # noqa: F821
    media_assets: Mapped[list["MediaAsset"]] = relationship(  # noqa: F821
        back_populates="video_scene"
    )
