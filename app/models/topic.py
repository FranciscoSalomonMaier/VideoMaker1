import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Topic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "topics"

    trend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    relevance_score: Mapped[float | None] = mapped_column(Float)

    trend: Mapped["Trend"] = relationship(back_populates="topics")  # noqa: F821
    video_projects: Mapped[list["VideoProject"]] = relationship(  # noqa: F821
        back_populates="topic"
    )
