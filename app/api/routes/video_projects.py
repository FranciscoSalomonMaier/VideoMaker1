from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.video_project import VideoProjectCreate, VideoProjectResponse
from app.use_cases import CreateVideoProject, CreateVideoProjectCommand, TopicNotFoundError

router = APIRouter(prefix="/video-projects", tags=["video-projects"])


@router.post("", response_model=VideoProjectResponse, status_code=status.HTTP_201_CREATED)
def create_video_project(
    payload: VideoProjectCreate,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VideoProjectResponse:
    use_case = CreateVideoProject(session=session, projects_dir=settings.projects_dir)
    command = CreateVideoProjectCommand(**payload.model_dump())

    try:
        project = use_case.execute(command)
    except TopicNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        ) from error

    return VideoProjectResponse.model_validate(project)
