import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import VideoProject, VideoProjectStatus, VideoScene
from app.providers import LLMProvider
from app.schemas.script import GeneratedScript

logger = logging.getLogger(__name__)


class ProjectNotFoundError(Exception):
    pass


class ScriptGenerationError(Exception):
    pass


class ScriptGenerator:
    def __init__(
        self,
        session: Session,
        provider: LLMProvider,
        prompts_dir: Path,
        projects_dir: Path,
    ) -> None:
        self.session = session
        self.provider = provider
        self.prompts_dir = prompts_dir
        self.projects_dir = projects_dir

    def generate(self, project_id: UUID) -> GeneratedScript:
        project = self.session.get(VideoProject, project_id)
        if project is None:
            raise ProjectNotFoundError(f"Video project {project_id} was not found")

        project.status = VideoProjectStatus.SCRIPT_GENERATING
        self.session.commit()

        try:
            result = self._request_script(project)
            self._save_result(project, result)
            return result
        except Exception as error:
            self.session.rollback()
            self._record_failure(project_id, error)
            if isinstance(error, ScriptGenerationError):
                raise
            raise ScriptGenerationError(f"Could not generate script for {project_id}") from error

    def retry(self, project_id: UUID) -> GeneratedScript:
        """Executa uma nova tentativa sem remover o projeto ou artefatos anteriores."""
        return self.generate(project_id)

    def _request_script(self, project: VideoProject) -> GeneratedScript:
        system_prompt = self._load_prompt("script_system.txt")
        user_template = self._load_prompt("script_user.txt")
        user_prompt = user_template.format(
            title=project.title,
            language=project.language,
            duration_minutes=project.duration_minutes,
            format=project.format,
        )
        response = self.provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=GeneratedScript,
        )
        try:
            return GeneratedScript.model_validate(response)
        except ValidationError as error:
            raise ScriptGenerationError("LLM response does not match the script schema") from error

    def _save_result(self, project: VideoProject, result: GeneratedScript) -> None:
        project.summary = result.summary
        project.script = result.script
        project.scenes.clear()
        project.scenes.extend(
            VideoScene(
                position=position,
                title=scene.title,
                narration=scene.narration,
                visual_description=scene.visual_description,
                duration_seconds=scene.duration_seconds,
            )
            for position, scene in enumerate(result.scenes, start=1)
        )
        project.status = VideoProjectStatus.SCRIPT_READY

        output_path = self.projects_dir / str(project.id) / "scripts" / "script.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            result.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            self.session.commit()
            temporary_path.replace(output_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def _record_failure(self, project_id: UUID, error: Exception) -> None:
        logger.exception("Script generation failed for project %s", project_id, exc_info=error)
        project = self.session.get(VideoProject, project_id)
        if project is not None:
            project.status = VideoProjectStatus.FAILED
            self.session.commit()

        error_path = self.projects_dir / str(project_id) / "scripts" / "errors.jsonl"
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
            logger.exception("Could not persist script generation error for %s", project_id)

    def _load_prompt(self, filename: str) -> str:
        path = self.prompts_dir / filename
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise ScriptGenerationError(f"Could not load prompt: {path}") from error
