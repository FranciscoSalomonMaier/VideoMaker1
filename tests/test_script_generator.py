import json
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Topic, Trend, VideoProject, VideoProjectStatus, VideoScene
from app.schemas.script import GeneratedScript
from app.services import ScriptGenerationError, ScriptGenerator


class FakeProvider:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
    ) -> BaseModel:
        self.calls.append({"system": system_prompt, "user": user_prompt, "model": response_model})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database_session:
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def project(session: Session, tmp_path: Path) -> VideoProject:
    trend = Trend(source="test", title="Tecnologia", observed_at=datetime.now(UTC))
    topic = Topic(title="Computação quântica", trend=trend)
    project = VideoProject(topic=topic, title=topic.title, duration_minutes=5)
    session.add(project)
    session.commit()
    (tmp_path / str(project.id) / "scripts").mkdir(parents=True)
    return project


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "script_system.txt").write_text("SYSTEM", encoding="utf-8")
    (prompts / "script_user.txt").write_text(
        "Tema={title}; idioma={language}; duração={duration_minutes}; formato={format}",
        encoding="utf-8",
    )
    return prompts


def valid_script() -> GeneratedScript:
    return GeneratedScript.model_validate(
        {
            "summary": "Uma introdução ao tema.",
            "script": "Primeira parte. Segunda parte.",
            "scenes": [
                {
                    "title": "Abertura",
                    "narration": "Primeira parte.",
                    "visual_description": "Título animado",
                    "duration_seconds": 12,
                },
                {
                    "title": "Explicação",
                    "narration": "Segunda parte.",
                    "visual_description": "Diagrama",
                    "duration_seconds": 18,
                },
            ],
        }
    )


def test_generates_validated_script_file_and_scenes(
    session: Session, project: VideoProject, prompts_dir: Path, tmp_path: Path
) -> None:
    provider = FakeProvider([valid_script()])
    service = ScriptGenerator(session, provider, prompts_dir, tmp_path)

    result = service.generate(project.id)

    session.refresh(project)
    scenes = session.scalars(
        select(VideoScene)
        .where(VideoScene.video_project_id == project.id)
        .order_by(VideoScene.position)
    ).all()
    artifact = json.loads(
        (tmp_path / str(project.id) / "scripts" / "script.json").read_text(encoding="utf-8")
    )
    assert result == valid_script()
    assert project.status is VideoProjectStatus.SCRIPT_READY
    assert project.script == result.script
    assert [scene.position for scene in scenes] == [1, 2]
    assert artifact == result.model_dump(mode="json")
    assert provider.calls[0]["system"] == "SYSTEM"
    assert "Tema=Computação quântica" in provider.calls[0]["user"]
    assert provider.calls[0]["model"] is GeneratedScript


def test_failure_is_recorded_and_retry_replaces_scenes(
    session: Session, project: VideoProject, prompts_dir: Path, tmp_path: Path
) -> None:
    provider = FakeProvider([RuntimeError("temporary outage"), valid_script()])
    service = ScriptGenerator(session, provider, prompts_dir, tmp_path)

    with pytest.raises(ScriptGenerationError):
        service.generate(project.id)

    assert session.get(VideoProject, project.id) is not None
    assert project.status is VideoProjectStatus.FAILED
    error_lines = (
        tmp_path / str(project.id) / "scripts" / "errors.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert json.loads(error_lines[0])["message"] == "temporary outage"

    service.retry(project.id)

    session.refresh(project)
    assert project.status is VideoProjectStatus.SCRIPT_READY
    assert len(project.scenes) == 2
