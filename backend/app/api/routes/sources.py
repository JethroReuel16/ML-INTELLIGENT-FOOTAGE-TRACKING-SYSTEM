
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

import cv2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(
    prefix="/api/sources",
    tags=["Video Sources"],
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(CURRENT_DIR)
    )
)

DATA_DIR = os.path.join(BACKEND_DIR, "data")
SOURCES_FILE = os.path.join(DATA_DIR, "video_sources.json")

os.makedirs(DATA_DIR, exist_ok=True)

_FILE_LOCK = threading.Lock()


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_sources() -> List[Dict[str, Any]]:
    with _FILE_LOCK:
        if not os.path.isfile(SOURCES_FILE):
            return []

        try:
            with open(
                SOURCES_FILE,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            return data if isinstance(data, list) else []

        except (OSError, json.JSONDecodeError):
            raise HTTPException(
                status_code=500,
                detail="Unable to read the video source registry.",
            )


def save_sources(
    sources: List[Dict[str, Any]],
) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    temporary_file = SOURCES_FILE + ".tmp"

    with _FILE_LOCK:
        try:
            with open(
                temporary_file,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    sources,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            os.replace(
                temporary_file,
                SOURCES_FILE,
            )

        except OSError as error:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to save video sources: {error}",
            )


def validate_source_type(
    source_type: str,
    url: str,
) -> str:
    normalized_type = source_type.strip().lower()

    if normalized_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "source_type must be rtsp, http, local, or network."
            ),
        )

    url = url.strip()

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

    return normalized_type


def mask_source_url(url: str) -> str:
    """
    Hide username/password in URL responses while retaining
    the host, port, path, and query for identification.
    """
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


def public_source(
    source: Dict[str, Any],
) -> Dict[str, Any]:
    result = dict(source)

    raw_url = result.pop("url", "")

    result["display_url"] = mask_source_url(raw_url)
    result["has_credentials"] = (
        "://" in raw_url
        and (
            urlsplit(raw_url).username is not None
            or urlsplit(raw_url).password is not None
        )
    )

    return result


def find_source(
    sources: List[Dict[str, Any]],
    source_id: str,
) -> Dict[str, Any]:
    for source in sources:
        if source.get("id") == source_id:
            return source

    raise HTTPException(
        status_code=404,
        detail=f"Video source not found: {source_id}",
    )


@router.get("")
def list_video_sources() -> List[Dict[str, Any]]:
    sources = load_sources()

    sources.sort(
        key=lambda source: source.get("created_at", ""),
        reverse=True,
    )

    return [
        public_source(source)
        for source in sources
    ]


@router.post("", status_code=201)
def create_video_source(
    payload: VideoSourceCreate,
) -> Dict[str, Any]:
    normalized_type = validate_source_type(
        payload.source_type,
        payload.url,
    )

    sources = load_sources()

    source = {
        "id": f"source_{uuid.uuid4().hex[:12]}",
        "name": payload.name.strip(),
        "source_type": normalized_type,
        "url": payload.url.strip(),
        "location": (payload.location or "").strip(),
        "description": (payload.description or "").strip(),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "last_tested_at": None,
        "last_connection_status": "not_tested",
    }

    sources.append(source)
    save_sources(sources)

    return public_source(source)


@router.get("/{source_id}")
def get_video_source(
    source_id: str,
) -> Dict[str, Any]:
    sources = load_sources()
    source = find_source(sources, source_id)

    return public_source(source)


@router.patch("/{source_id}")
def update_video_source(
    source_id: str,
    payload: VideoSourceUpdate,
) -> Dict[str, Any]:
    sources = load_sources()
    source = find_source(sources, source_id)

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
            source["source_type"],
        )

        normalized_type = validate_source_type(
            new_type,
            new_url,
        )

        source["url"] = new_url
        source["source_type"] = normalized_type

        changes.pop("url", None)
        changes.pop("source_type", None)

    elif (
        "source_type" in changes
        and changes["source_type"] is not None
    ):
        normalized_type = changes["source_type"].strip().lower()

        if normalized_type != source["source_type"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Provide a new URL when changing the source type."
                ),
            )

        changes["source_type"] = normalized_type

    for key, value in changes.items():
        if value is not None:
            source[key] = value

    source["updated_at"] = utc_now()

    save_sources(sources)

    return public_source(source)


@router.delete("/{source_id}")
def delete_video_source(
    source_id: str,
) -> Dict[str, Any]:
    sources = load_sources()
    find_source(sources, source_id)

    updated_sources = [
        source
        for source in sources
        if source.get("id") != source_id
    ]

    save_sources(updated_sources)

    return {
        "success": True,
        "message": "Video source deleted successfully.",
        "source_id": source_id,
    }


@router.post("/{source_id}/test")
def test_video_source(
    source_id: str,
) -> Dict[str, Any]:
    sources = load_sources()
    source = find_source(sources, source_id)

    tested_at = utc_now()
    connected = False
    error_message = None
    width = None
    height = None

    capture = None

    try:
        # Network capture must be performed by the backend,
        # not directly by the browser.
        capture = cv2.VideoCapture(
            source["url"],
            cv2.CAP_FFMPEG,
        )

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
        # Do not return the full exception because it might contain
        # credentials embedded in the source address.
        print(
            f"Video source test failed for {source_id}: "
            f"{type(error).__name__}"
        )

        error_message = (
            "The connection test failed. Check the source settings "
            "and backend logs."
        )

    finally:
        if capture is not None:
            capture.release()

    for item in sources:
        if item.get("id") == source_id:
            item["last_tested_at"] = tested_at
            item["last_connection_status"] = (
                "connected" if connected else "failed"
            )
            item["updated_at"] = utc_now()
            break

    save_sources(sources)

    return {
        "source_id": source_id,
        "connected": connected,
        "status": "connected" if connected else "failed",
        "tested_at": tested_at,
        "width": width,
        "height": height,
        "message": (
            "Connection successful. A video frame was received."
            if connected
            else error_message
        ),
    }