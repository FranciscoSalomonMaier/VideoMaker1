import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    MediaAsset,
    MetricSnapshot,
    Publication,
    Topic,
    Trend,
    VideoProject,
    VideoProjectStatus,
    VideoScene,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as database_session:
        yield database_session

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_create_complete_video_project_graph(session: Session) -> None:
    now = datetime.now(UTC)
    trend = Trend(
        source="google_trends",
        title="Novo modelo de IA",
        score=92.5,
        observed_at=now,
        raw_data={"region": "BR"},
    )
    topic = Topic(title="Impacto do novo modelo", relevance_score=0.95, trend=trend)
    project = VideoProject(title="O que muda com o novo modelo?", topic=topic)
    scene = VideoScene(
        position=1,
        narration="Conheça as principais mudanças.",
        duration_seconds=12.5,
        video_project=project,
    )
    asset = MediaAsset(
        asset_type="image",
        uri="assets/model.png",
        video_project=project,
        video_scene=scene,
    )
    publication = Publication(title=project.title, video_project=project)
    snapshot = MetricSnapshot(
        publication=publication,
        captured_at=now,
        view_count=100,
        like_count=10,
        comment_count=2,
    )

    session.add(trend)
    session.commit()

    stored_project = session.scalar(select(VideoProject))

    assert stored_project is not None
    assert isinstance(stored_project.id, uuid.UUID)
    assert stored_project.status is VideoProjectStatus.DRAFT
    assert stored_project.topic.trend is trend
    assert stored_project.scenes == [scene]
    assert stored_project.media_assets == [asset]
    assert stored_project.publications == [publication]
    assert publication.metric_snapshots == [snapshot]


def test_video_project_status_is_persisted(session: Session) -> None:
    trend = Trend(source="youtube", title="Tecnologia em alta", observed_at=datetime.now(UTC))
    topic = Topic(title="Pauta", trend=trend)
    project = VideoProject(
        title="Projeto em revisão",
        topic=topic,
        status=VideoProjectStatus.REVIEW_REQUIRED,
    )
    session.add(project)
    session.commit()
    session.expire_all()

    stored_project = session.scalar(select(VideoProject).where(VideoProject.id == project.id))

    assert stored_project is not None
    assert stored_project.status is VideoProjectStatus.REVIEW_REQUIRED


def test_deleting_project_cascades_to_owned_entities(session: Session) -> None:
    trend = Trend(source="news", title="Tendência", observed_at=datetime.now(UTC))
    topic = Topic(title="Pauta", trend=trend)
    project = VideoProject(title="Projeto", topic=topic)
    project.scenes.append(VideoScene(position=1, narration="Cena"))
    project.media_assets.append(MediaAsset(asset_type="audio", uri="assets/audio.mp3"))
    project.publications.append(Publication(title="Publicação"))
    session.add(project)
    session.commit()

    session.delete(project)
    session.commit()

    assert session.scalar(select(VideoScene)) is None
    assert session.scalar(select(MediaAsset)) is None
    assert session.scalar(select(Publication)) is None
