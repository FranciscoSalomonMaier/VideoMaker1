import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Topic, VideoProject

PROJECT_DIRECTORIES = ("research", "scripts", "audio", "assets", "renders")


class TopicNotFoundError(Exception):
    def __init__(self, topic_id: UUID) -> None:
        super().__init__(f"Topic {topic_id} was not found")
        self.topic_id = topic_id


@dataclass(frozen=True, slots=True)
class CreateVideoProjectCommand:
    topic_id: UUID
    language: str
    duration_minutes: int
    format: str


class CreateVideoProject:
    def __init__(self, session: Session, projects_dir: Path) -> None:
        self.session = session
        self.projects_dir = projects_dir

    def execute(self, command: CreateVideoProjectCommand) -> VideoProject:
        topic = self.session.get(Topic, command.topic_id)
        if topic is None:
            raise TopicNotFoundError(command.topic_id)

        project = VideoProject(
            topic=topic,
            title=topic.title,
            language=command.language,
            duration_minutes=command.duration_minutes,
            format=command.format,
        )
        self.session.add(project)

        project_dir: Path | None = None
        structure_created = False
        try:
            self.session.flush()
            self.session.refresh(project)
            project_dir = self.projects_dir / str(project.id)
            self._create_project_files(project, project_dir)
            structure_created = True
            self.session.commit()
        except Exception:
            self.session.rollback()
            if project_dir is not None and structure_created:
                self._remove_created_structure(project_dir)
            raise

        return project

    def _create_project_files(self, project: VideoProject, project_dir: Path) -> None:
        project_dir.mkdir(parents=True, exist_ok=False)
        try:
            for directory in PROJECT_DIRECTORIES:
                (project_dir / directory).mkdir()

            manifest = {
                "id": str(project.id),
                "topic_id": str(project.topic_id),
                "title": project.title,
                "language": project.language,
                "duration_minutes": project.duration_minutes,
                "format": project.format,
                "status": project.status.value,
                "created_at": project.created_at.isoformat(),
            }
            (project_dir / "project.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception:
            self._remove_created_structure(project_dir)
            raise

    @staticmethod
    def _remove_created_structure(project_dir: Path) -> None:
        manifest = project_dir / "project.json"
        if manifest.exists():
            manifest.unlink()
        for directory in reversed(PROJECT_DIRECTORIES):
            path = project_dir / directory
            if path.exists():
                path.rmdir()
        if project_dir.exists():
            project_dir.rmdir()
