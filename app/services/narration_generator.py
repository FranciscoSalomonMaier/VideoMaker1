import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import MediaAsset, VideoProject, VideoProjectStatus, VideoScene
from app.providers.text_to_speech import TextToSpeechProvider, TransientTextToSpeechError
from app.services.audio_duration import AudioDurationProbe, FFprobeAudioDurationProbe

logger = logging.getLogger(__name__)
AUDIO_ASSET_TYPE = "narration_audio"


class NarrationProjectNotFoundError(Exception):
    pass


class NarrationGenerationError(Exception):
    pass


class NarrationGenerator:
    def __init__(
        self,
        session: Session,
        provider: TextToSpeechProvider,
        projects_dir: Path,
        *,
        duration_probe: AudioDurationProbe | None = None,
        max_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.session = session
        self.provider = provider
        self.projects_dir = projects_dir
        self.duration_probe = duration_probe or FFprobeAudioDurationProbe()
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.sleep = sleep

    def generate(self, project_id: UUID) -> list[MediaAsset]:
        project = self.session.scalar(
            select(VideoProject)
            .where(VideoProject.id == project_id)
            .options(selectinload(VideoProject.scenes))
        )
        if project is None:
            raise NarrationProjectNotFoundError(f"Video project {project_id} was not found")

        project.status = VideoProjectStatus.AUDIO_GENERATING
        self.session.commit()
        assets: list[MediaAsset] = []
        try:
            for scene in project.scenes:
                assets.append(self._generate_scene(project, scene))
            project.status = VideoProjectStatus.ASSETS_GENERATING
            self.session.commit()
            return assets
        except Exception as error:
            self.session.rollback()
            self._record_failure(project_id, error)
            if isinstance(error, NarrationGenerationError):
                raise
            raise NarrationGenerationError(
                f"Could not generate narration for project {project_id}"
            ) from error

    def retry(self, project_id: UUID) -> list[MediaAsset]:
        return self.generate(project_id)

    def _generate_scene(self, project: VideoProject, scene: VideoScene) -> MediaAsset:
        existing = self.session.scalar(
            select(MediaAsset).where(
                MediaAsset.video_scene_id == scene.id,
                MediaAsset.asset_type == AUDIO_ASSET_TYPE,
            )
        )
        if existing is not None:
            existing_path = self.projects_dir / str(project.id) / existing.uri
            if existing_path.is_file():
                scene.duration_seconds = self.duration_probe.get_duration_seconds(existing_path)
                self.session.commit()
                return existing

        relative_path = Path("audio") / (
            f"scene_{scene.position:03d}_{scene.id}.{self.provider.audio_extension.lstrip('.')}"
        )
        output_path = self.projects_dir / str(project.id) / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
        temporary_path.unlink(missing_ok=True)

        try:
            self._synthesize_with_retry(scene.narration, temporary_path)
            duration = self.duration_probe.get_duration_seconds(temporary_path)
            temporary_path.replace(output_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        scene.duration_seconds = duration
        asset = existing or MediaAsset(
            video_project_id=project.id,
            video_scene_id=scene.id,
            asset_type=AUDIO_ASSET_TYPE,
            uri=relative_path.as_posix(),
        )
        asset.source = self.provider.name
        asset.uri = relative_path.as_posix()
        asset.asset_metadata = {"duration_seconds": duration}
        self.session.add(asset)
        self.session.commit()
        return asset

    def _synthesize_with_retry(self, narration: str, output_path: Path) -> None:
        for attempt in range(1, self.max_attempts + 1):
            try:
                self.provider.synthesize(text=narration, output_path=output_path)
                return
            except TransientTextToSpeechError:
                output_path.unlink(missing_ok=True)
                if attempt == self.max_attempts:
                    raise
                self.sleep(self.retry_delay_seconds * (2 ** (attempt - 1)))

    def _record_failure(self, project_id: UUID, error: Exception) -> None:
        logger.exception("Narration generation failed for project %s", project_id, exc_info=error)
        project = self.session.get(VideoProject, project_id)
        if project is not None:
            project.status = VideoProjectStatus.FAILED
            self.session.commit()

        error_path = self.projects_dir / str(project_id) / "audio" / "errors.jsonl"
        try:
            error_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "error_type": type(error).__name__,
                "message": str(error),
            }
            with error_path.open("a", encoding="utf-8") as error_file:
                error_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            logger.exception("Could not persist narration error for %s", project_id)
