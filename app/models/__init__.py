"""Modelos SQLAlchemy da aplicação."""

from app.models.media_asset import MediaAsset
from app.models.metric_snapshot import MetricSnapshot
from app.models.publication import Publication
from app.models.topic import Topic
from app.models.trend import Trend
from app.models.video_project import VideoProject, VideoProjectStatus
from app.models.video_scene import VideoScene

__all__ = [
    "MediaAsset",
    "MetricSnapshot",
    "Publication",
    "Topic",
    "Trend",
    "VideoProject",
    "VideoProjectStatus",
    "VideoScene",
]
