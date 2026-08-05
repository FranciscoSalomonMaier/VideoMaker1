import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Topic, Trend, VideoProject, VideoProjectStatus
from app.use_cases import CreateVideoProject, CreateVideoProjectCommand, TopicNotFoundError
from app.use_cases.create_video_project import PROJECT_DIRECTORIES


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database_session:
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def topic(session: Session) -> Topic:
    trend = Trend(source="test", title="IA em alta", observed_at=datetime.now(UTC))
    topic = Topic(title="O futuro da IA", trend=trend)
    session.add(topic)
    session.commit()
    return topic


def test_create_video_project_use_case(session: Session, topic: Topic, tmp_path: Path) -> None:
    command = CreateVideoProjectCommand(
        topic_id=topic.id,
        language="pt-BR",
        duration_minutes=7,
        format="faceless",
    )

    project = CreateVideoProject(session, tmp_path).execute(command)

    stored_project = session.scalar(select(VideoProject).where(VideoProject.id == project.id))
    project_dir = tmp_path / str(project.id)
    manifest = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))

    assert stored_project is project
    assert project.title == topic.title
    assert project.status is VideoProjectStatus.DRAFT
    assert manifest == {
        "id": str(project.id),
        "topic_id": str(topic.id),
        "title": topic.title,
        "language": "pt-BR",
        "duration_minutes": 7,
        "format": "faceless",
        "status": "DRAFT",
        "created_at": project.created_at.isoformat(),
    }
    assert all((project_dir / directory).is_dir() for directory in PROJECT_DIRECTORIES)


def test_create_video_project_rejects_unknown_topic(session: Session, tmp_path: Path) -> None:
    command = CreateVideoProjectCommand(
        topic_id=uuid.uuid4(),
        language="pt-BR",
        duration_minutes=7,
        format="faceless",
    )

    with pytest.raises(TopicNotFoundError):
        CreateVideoProject(session, tmp_path).execute(command)

    assert list(tmp_path.iterdir()) == []


def test_post_video_projects(session: Session, topic: Topic, tmp_path: Path) -> None:
    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: Settings(projects_dir=tmp_path)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/video-projects",
                json={
                    "topic_id": str(topic.id),
                    "language": "pt-BR",
                    "duration_minutes": 6,
                    "format": "faceless",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["topic_id"] == str(topic.id)
    assert body["title"] == topic.title
    assert body["status"] == "DRAFT"
    assert (tmp_path / body["id"] / "project.json").is_file()


def test_post_video_projects_returns_404_for_unknown_topic(
    session: Session, tmp_path: Path
) -> None:
    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: Settings(projects_dir=tmp_path)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/video-projects",
                json={
                    "topic_id": "00000000-0000-0000-0000-000000000000",
                    "language": "pt-BR",
                    "duration_minutes": 6,
                    "format": "faceless",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Topic not found"}
