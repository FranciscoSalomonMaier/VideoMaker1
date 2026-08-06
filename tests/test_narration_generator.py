from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import MediaAsset, Topic, Trend, VideoProject, VideoProjectStatus, VideoScene
from app.providers.text_to_speech import TransientTextToSpeechError
from app.services.narration_generator import (
    AUDIO_ASSET_TYPE,
    NarrationGenerationError,
    NarrationGenerator,
)


class FakeTextToSpeechProvider:
    name = "fake-tts"
    audio_extension = "mp3"

    def __init__(self, failure_calls: set[int] | None = None) -> None:
        self.failure_calls = failure_calls or set()
        self.calls: list[str] = []

    def synthesize(self, *, text: str, output_path: Path) -> None:
        self.calls.append(text)
        if len(self.calls) in self.failure_calls:
            raise TransientTextToSpeechError("provider unavailable")
        output_path.write_bytes(f"audio:{text}".encode())


class FakeDurationProbe:
    def __init__(self, duration: float = 4.25) -> None:
        self.duration = duration
        self.paths: list[Path] = []

    def get_duration_seconds(self, audio_path: Path) -> float:
        assert audio_path.is_file()
        self.paths.append(audio_path)
        return self.duration


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
    trend = Trend(source="test", title="Voz", observed_at=datetime.now(UTC))
    topic = Topic(title="Narração", trend=trend)
    project = VideoProject(
        topic=topic,
        title=topic.title,
        status=VideoProjectStatus.SCRIPT_READY,
        scenes=[
            VideoScene(position=1, narration="Primeira cena"),
            VideoScene(position=2, narration="Segunda cena"),
        ],
    )
    session.add(project)
    session.commit()
    (tmp_path / str(project.id) / "audio").mkdir(parents=True)
    return project


def test_generates_audio_updates_duration_and_saves_media_assets(
    session: Session, project: VideoProject, tmp_path: Path
) -> None:
    provider = FakeTextToSpeechProvider()
    probe = FakeDurationProbe(6.5)
    generator = NarrationGenerator(
        session, provider, tmp_path, duration_probe=probe, sleep=lambda _: None
    )

    assets = generator.generate(project.id)

    stored_assets = session.scalars(
        select(MediaAsset).where(MediaAsset.asset_type == AUDIO_ASSET_TYPE)
    ).all()
    assert project.status is VideoProjectStatus.ASSETS_GENERATING
    assert provider.calls == ["Primeira cena", "Segunda cena"]
    assert len(assets) == len(stored_assets) == 2
    assert [scene.duration_seconds for scene in project.scenes] == [6.5, 6.5]
    for asset in assets:
        assert asset.source == "fake-tts"
        assert asset.asset_metadata == {"duration_seconds": 6.5}
        assert (tmp_path / str(project.id) / asset.uri).is_file()


def test_reuses_existing_audio_without_calling_provider(
    session: Session, project: VideoProject, tmp_path: Path
) -> None:
    provider = FakeTextToSpeechProvider()
    probe = FakeDurationProbe()
    generator = NarrationGenerator(session, provider, tmp_path, duration_probe=probe)
    first_assets = generator.generate(project.id)

    provider.calls.clear()
    reused_assets = generator.retry(project.id)

    assert provider.calls == []
    assert [asset.id for asset in reused_assets] == [asset.id for asset in first_assets]
    assert len(session.scalars(select(MediaAsset)).all()) == 2
    assert len(probe.paths) == 4


def test_retries_transient_provider_failure(
    session: Session, project: VideoProject, tmp_path: Path
) -> None:
    provider = FakeTextToSpeechProvider(failure_calls={1, 2})
    delays: list[float] = []
    generator = NarrationGenerator(
        session,
        provider,
        tmp_path,
        duration_probe=FakeDurationProbe(),
        max_attempts=3,
        retry_delay_seconds=0.5,
        sleep=delays.append,
    )

    generator.generate(project.id)

    assert provider.calls[:3] == ["Primeira cena"] * 3
    assert delays == [0.5, 1.0]
    assert project.status is VideoProjectStatus.ASSETS_GENERATING


def test_retry_reuses_completed_scenes_after_exhausted_transient_failure(
    session: Session, project: VideoProject, tmp_path: Path
) -> None:
    provider = FakeTextToSpeechProvider(failure_calls={2})
    generator = NarrationGenerator(
        session,
        provider,
        tmp_path,
        duration_probe=FakeDurationProbe(),
        max_attempts=1,
        sleep=lambda _: None,
    )

    with pytest.raises(NarrationGenerationError):
        generator.generate(project.id)

    assert project.status is VideoProjectStatus.FAILED
    assert len(session.scalars(select(MediaAsset)).all()) == 1
    assert (
        tmp_path / str(project.id) / "audio" / "errors.jsonl"
    ).is_file()

    generator.retry(project.id)

    assert project.status is VideoProjectStatus.ASSETS_GENERATING
    assert len(session.scalars(select(MediaAsset)).all()) == 2
    assert provider.calls.count("Primeira cena") == 1
