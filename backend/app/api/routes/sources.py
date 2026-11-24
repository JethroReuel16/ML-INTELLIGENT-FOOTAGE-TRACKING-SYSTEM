
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import cv2

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.database import get_db
from app.models import VideoSource
from app.source_policy import check_source


logger = logging.getLogger(__name__)

FILE_SOURCE_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v", ".mpeg", ".mpg"
}

# Connection-test timeouts so an unreachable camera cannot hang a worker.
TEST_OPEN_TIMEOUT_MS = 10000
TEST_READ_TIMEOUT_MS = 10000

router = APIRouter(
    prefix="/api/sources",
    tags=["Video Sources"],
)


class VideoSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source_type: str
    url: str = Field(min_length=1, max_length=2048)
    location: Optional[str] = Field(default="", max_length=200)
    description: Optional[str] = Field(default="", max_length=500)


class VideoSourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    source_type: Optional[str] = None
    url: Optional[str] = Field(default=None, max_length=2048)
    location: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)


ALLOWED_TYPES = {
    "rtsp",
    "http",
    "local",
    "network",
}


def utc_now():
    return datetime.now(timezone.utc)


def validate_source_type(source_type: str, url: str) -> str:
    normalized_type = source_type.strip().lower()
    url = url.strip()

    if normalized_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="source_type must be rtsp, http, local, or network.",
        )

    if not url:
        raise HTTPException(
            status_code=400,
            detail="A video source URL or path is required.",
        )

    if "\x00" in url:
        raise HTTPException(
            status_code=400,
            detail="The source address contains invalid characters.",
        )

    if normalized_type == "rtsp":
        if not url.lower().startswith(("rtsp://", "rtsps://")):
            raise HTTPException(
                status_code=400,
                detail="RTSP sources must use rtsp:// or rtsps://.",
            )

    elif normalized_type == "http":
        if not url.lower().startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="HTTP video sources must use http:// or https://.",
            )

    elif normalized_type == "local":
        if url.lower().startswith(
            ("rtsp://", "rtsps://", "http://", "https://")
        ):
            raise HTTPException(
                status_code=400,
                detail="Choose the matching network source type for this URL.",
            )

    elif normalized_type == "network":
        if url.lower().startswith(
            ("rtsp://", "rtsps://", "http://", "https://")
        ):
            raise HTTPException(
                status_code=400,
                detail="Choose RTSP or HTTP for this URL.",
            )

        if not (
            url.startswith("\\\\")
            or url.startswith("//")
            or os.path.isabs(url)
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Use an absolute network path, such as "
                    r"\\server\share\camera.mp4"
                ),
            )

    if normalized_type in {"local", "network"}:
        extension = os.path.splitext(url.rstrip("\\/"))[1].lower()

        if extension not in FILE_SOURCE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Point the source at a specific video file "
                    "(MP4, AVI, MOV, MKV, WebM, M4V or MPEG), not a folder."
                ),
            )

    # Where the source may point (file allow-list, no SSRF targets).
    check_source(normalized_type, url)

    return normalized_type


def open_capture(url: str):
    """Open a video source with connection timeouts when OpenCV supports them."""
    try:
        return cv2.VideoCapture(
            url,
            cv2.CAP_FFMPEG,
            [
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, TEST_OPEN_TIMEOUT_MS,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC, TEST_READ_TIMEOUT_MS,
            ],
        )
    except (TypeError, cv2.error):
        return cv2.VideoCapture(url, cv2.CAP_FFMPEG)


def mask_source_url(url: str) -> str:
    try:
        parsed = urlsplit(url)

        if not parsed.scheme or not parsed.hostname:
            return url

        if parsed.username is None and parsed.password is None:
            return url

        host = parsed.hostname

        if ":" in host and not host.startswith("["):
            host = f"[{host}]"

        if parsed.port:
            host = f"{host}:{parsed.port}"

        return urlunsplit(
            (
                parsed.scheme,
                f"***:***@{host}",
                parsed.path,
                parsed.query,
                parsed.fragment,
            )
        )

    except (ValueError, TypeError):
        return "[address hidden]"


def public_source(source: VideoSource) -> Dict[str, Any]:
    raw_url = source.url or ""

    try:
        parsed = urlsplit(raw_url)

        has_credentials = (
            "://" in raw_url
            and (
                parsed.username is not None
                or parsed.password is not None
            )
        )
    except (ValueError, TypeError):
        has_credentials = False

    return {
        "id": source.id,
        "owner_id": str(source.owner_id) if source.owner_id is not None else None,
        "name": source.name,
        "source_type": source.source_type,
        "location": source.location,
        "description": source.description,
        "display_url": mask_source_url(raw_url),
        "has_credentials": has_credentials,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
        "last_tested_at": (
            source.last_tested_at.isoformat()
            if source.last_tested_at else None
        ),
        "last_connection_status": source.last_connection_status,
    }


def find_source(
    db: Session,
    source_id: str,
    owner_id: int,
) -> VideoSource:
    source = (
        db.query(VideoSource)
        .filter(
            VideoSource.id == source_id,
            VideoSource.owner_id == owner_id,
        )
        .first()
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="Video source not found.",
        )

    return source


def database_error():
    raise HTTPException(
        status_code=500,
        detail="A database operation failed. Please try again.",
    )


@router.get("")
def list_video_sources(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[Dict[str, Any]]:

    sources = (
        db.query(VideoSource)
        .filter(VideoSource.owner_id == current_user.id)
        .order_by(VideoSource.created_at.desc())
        .all()
    )

    return [public_source(source) for source in sources]


@router.post("", status_code=201)
def create_video_source(
    payload: VideoSourceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    normalized_type = validate_source_type(
        payload.source_type,
        payload.url,
    )

    source = VideoSource(
        id=f"source_{uuid.uuid4().hex[:12]}",
        owner_id=current_user.id,
        name=payload.name.strip(),
        source_type=normalized_type,
        url=payload.url.strip(),
        location=(payload.location or "").strip(),
        description=(payload.description or "").strip(),
        last_connection_status="not_tested",
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    try:
        db.add(source)
        db.commit()
        db.refresh(source)

        return public_source(source)

    except SQLAlchemyError:
        db.rollback()
        database_error()


@router.get("/{source_id}")
def get_video_source(
    source_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    source = find_source(
        db,
        source_id,
        current_user.id,
    )

    return public_source(source)


@router.patch("/{source_id}")
def update_video_source(
    source_id: str,
    payload: VideoSourceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    source = find_source(
        db,
        source_id,
        current_user.id,
    )

    changes = payload.model_dump(exclude_unset=True)

    if "name" in changes and changes["name"] is not None:
        changes["name"] = changes["name"].strip()

    if "location" in changes and changes["location"] is not None:
        changes["location"] = changes["location"].strip()

    if "description" in changes and changes["description"] is not None:
        changes["description"] = changes["description"].strip()

    new_url = changes.get("url")

    if new_url is not None:
        new_url = new_url.strip()

        new_type = changes.get(
            "source_type",
            source.source_type,
        )

        normalized_type = validate_source_type(
            new_type,
            new_url,
        )

        source.url = new_url
        source.source_type = normalized_type

        changes.pop("url", None)
        changes.pop("source_type", None)

    elif (
        "source_type" in changes
        and changes["source_type"] is not None
    ):
        normalized_type = changes["source_type"].strip().lower()

        if normalized_type != source.source_type:
            raise HTTPException(
                status_code=400,
                detail="Provide a new URL when changing the source type.",
            )

        source.source_type = normalized_type

        changes.pop("source_type", None)

    for key, value in changes.items():
        if value is not None:
            setattr(source, key, value)

    source.updated_at = utc_now()

    try:
        db.commit()
        db.refresh(source)

        return public_source(source)

    except SQLAlchemyError:
        db.rollback()
        database_error()


@router.delete("/{source_id}")
def delete_video_source(
    source_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    source = find_source(
        db,
        source_id,
        current_user.id,
    )

    try:
        db.delete(source)
        db.commit()

        return {
            "success": True,
            "message": "Video source deleted successfully.",
            "source_id": source_id,
        }

    except SQLAlchemyError:
        db.rollback()
        database_error()


@router.post("/{source_id}/test")
def test_video_source(
    source_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:

    source = find_source(
        db,
        source_id,
        current_user.id,
    )

    # Re-check on every use: the policy (or DNS) may have changed since the
    # source was registered.
    check_source(source.source_type, source.url)

    tested_at = utc_now()
    connected = False
    error_message = None
    width = None
    height = None
    capture = None

    try:
        capture = open_capture(source.url)

        if not capture.isOpened():
            error_message = (
                "Could not open the source. Check its address, "
                "credentials, network access, and stream availability."
            )
        else:
            success, frame = capture.read()

            if not success or frame is None:
                error_message = (
                    "The source opened but no video frame could be read."
                )
            else:
                connected = True
                height, width = frame.shape[:2]

    except Exception as error:
        logger.warning(
            "Video source test failed for %s: %s",
            source_id,
            type(error).__name__,
        )

        error_message = (
            "The connection test failed. Check the source settings "
            "and backend logs."
        )

    finally:
        if capture is not None:
            capture.release()

    source.last_tested_at = tested_at
    source.last_connection_status = (
        "connected" if connected else "failed"
    )
    source.updated_at = utc_now()

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        database_error()

    return {
        "source_id": source_id,
        "connected": connected,
        "status": "connected" if connected else "failed",
        "tested_at": tested_at.isoformat(),
        "width": width,
        "height": height,
        "message": (
            "Connection successful. A video frame was received."
            if connected
            else error_message
        ),
    }
