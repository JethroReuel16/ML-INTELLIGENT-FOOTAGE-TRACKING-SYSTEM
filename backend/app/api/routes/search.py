
import json
import logging
import os
import shutil
import uuid
import time

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import cv2

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    VideoSource,
    SearchRecord,
    SearchMatch,
    EvidenceFile,
    MultiSourceSearch,
    MultiSourceItem,
)

from app.config import settings
from app.storage import UPLOADS_DIR, RESULTS_DIR

from app.services.search_service import (
    DetectorCapabilityError,
    parse_text_prompts,
    resolve_search_mode,
    search_service,
)
from app.api.routes.auth import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/search",
    tags=["Search"],
)


# ---------------------------------------------------------
# SHARED PERSISTENT STORAGE
# ---------------------------------------------------------

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


MAX_HTTP_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = settings.max_video_upload_mb * 1024 * 1024
MAX_IMAGE_UPLOAD_BYTES = settings.max_image_upload_mb * 1024 * 1024
MAX_RESULTS_LIMIT = 100
COPY_CHUNK_BYTES = 1024 * 1024

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".webm",
    ".m4v", ".mpeg", ".mpg"
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp"
}


def utc_now():
    return datetime.now(timezone.utc)


def parse_datetime(value):
    if not value:
        return utc_now()

    try:
        if isinstance(value, datetime):
            return value

        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return utc_now()


def parse_int(value):
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def parse_float(value):
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def save_uploaded_file(
    upload_file: UploadFile,
    destination_folder: str,
    max_bytes: int,
    label: str = "file",
) -> str:
    """Stream an upload to disk, enforcing a size limit. Blocking: run in a thread."""

    os.makedirs(destination_folder, exist_ok=True)

    original_name = upload_file.filename or "uploaded_file"
    extension = os.path.splitext(original_name)[1].lower() or ".bin"

    unique_name = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(destination_folder, unique_name)

    total = 0
    upload_file.file.seek(0)

    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = upload_file.file.read(COPY_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"The {label} is too large. The limit is "
                            f"{max_bytes // (1024 * 1024)} MB."
                        ),
                    )
                buffer.write(chunk)
    except BaseException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    if total == 0:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"The uploaded {label} is empty.",
        )

    return file_path


def validate_video_upload(video: UploadFile) -> None:
    """Accept video/* uploads, or generic types with a known video extension."""

    content_type = (video.content_type or "").lower()
    extension = os.path.splitext(video.filename or "")[1].lower()

    if content_type.startswith("video/"):
        return

    if extension in ALLOWED_VIDEO_EXTENSIONS and content_type in {
        "", "application/octet-stream", "application/mp4",
    }:
        return

    raise HTTPException(
        status_code=400,
        detail=(
            "Uploaded file must be a video (MP4, AVI, MOV, MKV, WebM, "
            "M4V or MPEG)."
        ),
    )


def remove_request_folder(folder: str) -> None:
    """Delete a request's upload folder after a failed search."""
    shutil.rmtree(folder, ignore_errors=True)


def validate_search_parameters(
    frame_interval: int,
    min_detection_confidence: float,
    max_results: int,
) -> None:

    if frame_interval < 1:
        raise HTTPException(
            status_code=400,
            detail="frame_interval must be at least 1.",
        )

    if not 0 <= min_detection_confidence <= 1:
        raise HTTPException(
            status_code=400,
            detail="min_detection_confidence must be between 0 and 1.",
        )

    if not 1 <= max_results <= MAX_RESULTS_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"max_results must be between 1 and {MAX_RESULTS_LIMIT}.",
        )


def prepare_search_inputs(
    reference_image: Optional[UploadFile],
    text_prompt: Optional[str],
    search_mode: Optional[str],
):
    """
    Validate the image / text inputs and return (mode, clean_text).

    Image search is unchanged; text search and image + text search are
    additive. An empty file field counts as "no image".
    """

    has_image = bool(
        reference_image
        and (reference_image.filename or "").strip()
    )

    if has_image:
        validate_reference_image(reference_image)

    clean_text = ", ".join(parse_text_prompts(text_prompt)) or None

    try:
        mode = resolve_search_mode(
            "image" if has_image else None,
            clean_text,
            search_mode,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return mode, clean_text


def validate_reference_image(reference_image: UploadFile) -> None:

    if not reference_image.content_type:
        raise HTTPException(
            status_code=400,
            detail="Reference image content type is missing.",
        )

    if not reference_image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Reference file must be an image.",
        )

    extension = os.path.splitext(reference_image.filename or "")[1].lower()

    if extension and extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Reference image must be JPG, PNG, WebP or BMP.",
        )


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


def persist_search(
    db: Session,
    result: dict,
    owner_id: int,
    source_id: Optional[str] = None,
    fallback_search_id: Optional[str] = None,
):
    """
    Save a completed search, its summary, matches and evidence
    references to PostgreSQL.
    """

    if not isinstance(result, dict):
        raise RuntimeError(
            "The search pipeline returned an invalid result."
        )

    search_id = (
        result.get("search_id")
        or fallback_search_id
    )

    if not search_id:
        raise RuntimeError(
            "The search pipeline did not return a search ID."
        )

    existing = db.get(SearchRecord, search_id)

    if existing:
        return search_id

    video = result.get("video") or {}
    reference = result.get("reference") or {}
    settings = result.get("search") or {}
    matches = result.get("matches") or []

    summary_payload = {
        "status": result.get("status") or "completed",
        "search_id": search_id,
        "owner_id": str(owner_id),
        "created_at": result.get("created_at"),
        "video": video,
        "search": settings,
        "top_match": matches[0] if matches else None,
    }

    record = SearchRecord(
        id=search_id,
        owner_id=owner_id,
        source_id=source_id,
        status=result.get("status") or "completed",
        created_at=parse_datetime(result.get("created_at")),
        reference_data=reference,
        video_metadata=video,
        search_settings=settings,
        video_path=video.get("path"),
        reference_image_path=reference.get("image"),
        duration=parse_float(video.get("duration")),
        fps=parse_float(video.get("fps")),
        frame_count=parse_int(video.get("frame_count")),
        result_payload=result,
        summary_payload=summary_payload,
    )

    db.add(record)
    db.flush()

    for match_data in matches:

        if not isinstance(match_data, dict):
            continue

        match = SearchMatch(
            search_id=search_id,
            rank=parse_int(match_data.get("rank")),
            track_id=parse_int(match_data.get("track_id")),
            class_id=parse_int(match_data.get("class_id")),
            class_name=match_data.get("class_name"),
            match_status=match_data.get("match_status"),
            similarity_score=parse_float(
                match_data.get("similarity_score")
            ),
            ranking_score=parse_float(
                match_data.get("ranking_score")
            ),
            top3_average=parse_float(
                match_data.get("top3_average")
            ),
            average_similarity=parse_float(
                match_data.get("average_similarity")
            ),
            timestamp=parse_float(match_data.get("timestamp")),
            frame_number=parse_int(match_data.get("frame_number")),
            bbox=match_data.get("bbox"),
            detection_confidence=parse_float(
                match_data.get("detection_confidence")
            ),
            frames_observed=parse_int(
                match_data.get("frames_observed")
            ),
            evidence_image=match_data.get("evidence_image"),
            original_payload=match_data,
        )

        db.add(match)
        db.flush()

        evidence_path = match_data.get("evidence_image")

        if evidence_path:
            db.add(
                EvidenceFile(
                    search_id=search_id,
                    match_id=match.id,
                    file_path=str(evidence_path),
                    file_type="image",
                )
            )

    db.commit()

    return search_id


def run_pipeline_search(
    request_id: str,
    reference_path: Optional[str],
    video_path: str,
    frame_interval: int,
    min_detection_confidence: float,
    max_results: int,
    owner_id: int,
    db: Session,
    source_id: Optional[str] = None,
    text_prompt: Optional[str] = None,
    search_mode: Optional[str] = None,
    high_detail: bool = False,
) -> dict:

    logger.info(
        "Search %s started (owner=%s, mode=%s, source=%s)",
        request_id,
        owner_id,
        search_mode,
        source_id or "upload",
    )
    started = time.monotonic()

    result = search_service.run_search(
        reference_image=reference_path,
        video_path=video_path,
        frame_interval=frame_interval,
        min_detection_confidence=min_detection_confidence,
        max_results=max_results,
        owner_id=str(owner_id),
        text_prompt=text_prompt,
        search_mode=search_mode,
        high_detail=high_detail,
    )

    try:
        search_id = persist_search(
            db=db,
            result=result,
            owner_id=owner_id,
            source_id=source_id,
            fallback_search_id=request_id,
        )

    except Exception:
        db.rollback()
        raise

    result["search_id"] = search_id

    logger.info(
        "Search %s finished in %.1fs with %d match(es)",
        search_id,
        time.monotonic() - started,
        len(result.get("matches") or []),
    )

    return {
        "status": "completed",
        "message": "Search completed successfully.",
        "request_id": request_id,
        "result": result,
    }


def copy_recorded_file(
    source_path: str,
    destination_folder: str,
) -> str:

    path = Path(source_path)

    if settings.allowed_source_roots:
        real = os.path.realpath(str(path))
        allowed = False
        for root in settings.allowed_source_roots:
            root_real = os.path.realpath(root)
            try:
                if os.path.commonpath([real, root_real]) == root_real:
                    allowed = True
                    break
            except ValueError:
                continue
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="This source path is outside the directories the server may read.",
            )

    if not path.is_file():
        raise HTTPException(
            status_code=400,
            detail=(
                "The registered source is not an accessible video file. "
                "Register a specific video file, not just a folder."
            ),
        )

    extension = path.suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported video file type '{extension or 'none'}'. Use "
                "MP4, AVI, MOV, MKV, WebM, M4V or MPEG."
            ),
        )

    destination = os.path.join(
        destination_folder,
        f"source_video{extension or '.mp4'}",
    )

    try:
        shutil.copy2(str(path), destination)

    except OSError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to copy the registered video. Check backend "
                "permissions and available disk space."
            ),
        ) from error

    return destination


def download_http_video(
    source_url: str,
    destination_folder: str,
) -> str:

    parsed = urlsplit(source_url)
    extension = os.path.splitext(parsed.path)[1].lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        extension = ".mp4"

    destination = os.path.join(
        destination_folder,
        f"source_video{extension}",
    )

    request = Request(
        source_url,
        headers={"User-Agent": "MLFootageTracking/1.0"},
    )

    try:
        with urlopen(request, timeout=20) as response:

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if (
                content_type
                and not content_type.startswith("video/")
                and "octet-stream" not in content_type
                and "application/mp4" not in content_type
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "The HTTP source did not return a direct video file."
                    ),
                )

            total_bytes = 0

            with open(destination, "wb") as output:

                while True:
                    chunk = response.read(1024 * 1024)

                    if not chunk:
                        break

                    total_bytes += len(chunk)

                    if total_bytes > MAX_HTTP_DOWNLOAD_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail="The HTTP video exceeds the 2 GB limit.",
                        )

                    output.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="The HTTP source returned an empty file.",
            )

        return destination

    except HTTPException:
        if os.path.exists(destination):
            os.remove(destination)
        raise

    except Exception as error:
        if os.path.exists(destination):
            os.remove(destination)

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to download the HTTP video. Check the direct video "
                "URL, internet connection and server response."
            ),
        ) from error


def record_rtsp_window(
    source_url: str,
    destination_folder: str,
    duration_seconds: int,
) -> str:

    destination = os.path.join(
        destination_folder,
        "source_recording.mp4",
    )

    capture = None
    writer = None
    frames_written = 0
    start_time = time.monotonic()

    try:
        try:
            capture = cv2.VideoCapture(
                source_url,
                cv2.CAP_FFMPEG,
                [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000,
                ],
            )

        except (TypeError, cv2.error):
            capture = cv2.VideoCapture(
                source_url,
                cv2.CAP_FFMPEG,
            )

        if not capture.isOpened():
            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to open the RTSP stream. Check the stream URL, "
                    "credentials, network access and FFmpeg support."
                ),
            )

        fps = capture.get(cv2.CAP_PROP_FPS)

        if not fps or fps <= 0 or fps > 120:
            fps = 25.0

        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if width <= 0 or height <= 0:
            success, first_frame = capture.read()

            if not success or first_frame is None:
                raise HTTPException(
                    status_code=502,
                    detail="The RTSP stream returned no video frame.",
                )

            height, width = first_frame.shape[:2]

            writer = cv2.VideoWriter(
                destination,
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (width, height),
            )

            if not writer.isOpened():
                raise HTTPException(
                    status_code=500,
                    detail="Unable to create the temporary RTSP recording.",
                )

            writer.write(first_frame)
            frames_written += 1

        else:
            writer = cv2.VideoWriter(
                destination,
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (width, height),
            )

            if not writer.isOpened():
                raise HTTPException(
                    status_code=500,
                    detail="Unable to create the temporary RTSP recording.",
                )

        while time.monotonic() - start_time < duration_seconds:

            success, frame = capture.read()

            if not success or frame is None:
                break

            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height))

            writer.write(frame)
            frames_written += 1

        if frames_written == 0:
            raise HTTPException(
                status_code=502,
                detail="No frames were captured from the RTSP stream.",
            )

    finally:
        if capture is not None:
            capture.release()

        if writer is not None:
            writer.release()

    if (
        not os.path.isfile(destination)
        or os.path.getsize(destination) == 0
    ):
        raise HTTPException(
            status_code=500,
            detail="The RTSP recording could not be saved.",
        )

    return destination


def _search_failure(error: Exception, request_folder: str, db: Session, label: str):
    """Map a search exception to an HTTP error and clean up its uploads."""

    db.rollback()
    remove_request_folder(request_folder)

    if isinstance(error, HTTPException):
        return error

    if isinstance(error, DetectorCapabilityError):
        return HTTPException(status_code=400, detail=str(error))

    if isinstance(error, FileNotFoundError):
        return HTTPException(
            status_code=400,
            detail="The video could not be read. Check that it is a valid, playable video file.",
        )

    logger.exception("%s failed", label)

    return HTTPException(
        status_code=500,
        detail=f"{label} failed. Check the server logs for details.",
    )


@router.post("")
async def search_object(
    reference_image: Optional[UploadFile] = File(None),
    text_prompt: Optional[str] = Form(None),
    search_mode: Optional[str] = Form(None),
    video: UploadFile = File(...),
    frame_interval: int = Form(5),
    min_detection_confidence: float = Form(0.25),
    max_results: int = Form(20),
    high_detail: bool = Form(False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    search_mode, text_prompt = prepare_search_inputs(
        reference_image,
        text_prompt,
        search_mode,
    )

    validate_search_parameters(
        frame_interval,
        min_detection_confidence,
        max_results,
    )

    validate_video_upload(video)

    request_id = uuid.uuid4().hex
    request_folder = os.path.join(UPLOADS_DIR, request_id)

    os.makedirs(request_folder, exist_ok=True)

    try:
        # Everything below is blocking (disk I/O, ML inference, DB writes),
        # so it runs in a worker thread and never stalls the event loop.
        reference_path = (
            await run_in_threadpool(
                save_uploaded_file,
                reference_image,
                request_folder,
                MAX_IMAGE_UPLOAD_BYTES,
                "reference image",
            )
            if search_mode != "text"
            else None
        )

        video_path = await run_in_threadpool(
            save_uploaded_file,
            video,
            request_folder,
            MAX_VIDEO_UPLOAD_BYTES,
            "video",
        )

        return await run_in_threadpool(
            run_pipeline_search,
            request_id=request_id,
            reference_path=reference_path,
            video_path=video_path,
            frame_interval=frame_interval,
            min_detection_confidence=min_detection_confidence,
            max_results=max_results,
            owner_id=current_user.id,
            db=db,
            text_prompt=text_prompt,
            search_mode=search_mode,
            high_detail=high_detail,
        )

    except Exception as error:
        raise _search_failure(error, request_folder, db, "Search") from error


async def _run_source_search(
    *,
    source: VideoSource,
    reference_image: Optional[UploadFile],
    text_prompt: Optional[str],
    search_mode: str,
    frame_interval: int,
    min_detection_confidence: float,
    max_results: int,
    recording_duration_seconds: int,
    db: Session,
    owner_id: int,
    high_detail: bool = False,
) -> dict:
    """Fetch footage from a registered source and search it."""

    source_type = (source.source_type or "").strip().lower()
    source_url = (source.url or "").strip()

    if not source_url:
        raise HTTPException(
            status_code=400,
            detail="The registered source has no configured address.",
        )

    request_id = uuid.uuid4().hex
    request_folder = os.path.join(UPLOADS_DIR, request_id)

    os.makedirs(request_folder, exist_ok=True)

    try:
        reference_path = (
            await run_in_threadpool(
                save_uploaded_file,
                reference_image,
                request_folder,
                MAX_IMAGE_UPLOAD_BYTES,
                "reference image",
            )
            if search_mode != "text"
            else None
        )

        if source_type in {"local", "network"}:
            video_path = await run_in_threadpool(
                copy_recorded_file, source_url, request_folder
            )

        elif source_type == "http":
            video_path = await run_in_threadpool(
                download_http_video, source_url, request_folder
            )

        elif source_type == "rtsp":
            video_path = await run_in_threadpool(
                record_rtsp_window,
                source_url,
                request_folder,
                recording_duration_seconds,
            )

        else:
            raise HTTPException(
                status_code=400,
                detail="The registered source has an unsupported source type.",
            )

        response = await run_in_threadpool(
            run_pipeline_search,
            request_id=request_id,
            reference_path=reference_path,
            video_path=video_path,
            frame_interval=frame_interval,
            min_detection_confidence=min_detection_confidence,
            max_results=max_results,
            owner_id=owner_id,
            db=db,
            text_prompt=text_prompt,
            search_mode=search_mode,
            source_id=source.id,
            high_detail=high_detail,
        )

        response["source"] = {
            "id": source.id,
            "name": source.name,
            "source_type": source_type,
            "recording_duration_seconds": (
                recording_duration_seconds
                if source_type == "rtsp"
                else None
            ),
        }

        return response

    except Exception as error:
        raise _search_failure(
            error, request_folder, db, "Registered-source search"
        ) from error


@router.post("/source")
async def search_registered_source(
    source_id: str = Form(...),
    reference_image: Optional[UploadFile] = File(None),
    text_prompt: Optional[str] = Form(None),
    search_mode: Optional[str] = Form(None),
    frame_interval: int = Form(5),
    min_detection_confidence: float = Form(0.25),
    max_results: int = Form(20),
    high_detail: bool = Form(False),
    recording_duration_seconds: int = Form(30),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    search_mode, text_prompt = prepare_search_inputs(
        reference_image,
        text_prompt,
        search_mode,
    )

    validate_search_parameters(
        frame_interval,
        min_detection_confidence,
        max_results,
    )

    if not 5 <= recording_duration_seconds <= 300:
        raise HTTPException(
            status_code=400,
            detail="recording_duration_seconds must be between 5 and 300.",
        )

    source = find_source(
        db,
        source_id,
        current_user.id,
    )

    return await _run_source_search(
        source=source,
        reference_image=reference_image,
        text_prompt=text_prompt,
        search_mode=search_mode,
        frame_interval=frame_interval,
        min_detection_confidence=min_detection_confidence,
        max_results=max_results,
        recording_duration_seconds=recording_duration_seconds,
        db=db,
        owner_id=current_user.id,
        high_detail=high_detail,
    )


@router.post("/multi-source")
async def search_multiple_registered_sources(
    source_ids: str = Form(...),
    reference_image: Optional[UploadFile] = File(None),
    text_prompt: Optional[str] = Form(None),
    search_mode: Optional[str] = Form(None),
    frame_interval: int = Form(5),
    min_detection_confidence: float = Form(0.25),
    max_results: int = Form(20),
    high_detail: bool = Form(False),
    recording_duration_seconds: int = Form(30),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    search_mode, text_prompt = prepare_search_inputs(
        reference_image,
        text_prompt,
        search_mode,
    )

    validate_search_parameters(
        frame_interval,
        min_detection_confidence,
        max_results,
    )

    if not 5 <= recording_duration_seconds <= 300:
        raise HTTPException(
            status_code=400,
            detail="recording_duration_seconds must be between 5 and 300.",
        )

    try:
        selected_ids = json.loads(source_ids)

    except (TypeError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=400,
            detail="source_ids must be a JSON array of registered source IDs.",
        ) from error

    if (
        not isinstance(selected_ids, list)
        or not selected_ids
        or not all(
            isinstance(item, str) and item.strip()
            for item in selected_ids
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Select at least one valid registered source.",
        )

    selected_ids = list(
        dict.fromkeys(item.strip() for item in selected_ids)
    )

    if len(selected_ids) > 20:
        raise HTTPException(
            status_code=400,
            detail="A multi-source search can include at most 20 sources.",
        )

    selected_sources = {}

    for source_id in selected_ids:
        selected_sources[source_id] = find_source(
            db,
            source_id,
            current_user.id,
        )

    multi_id = uuid.uuid4().hex

    source_results = []
    combined_matches = []

    for source_id in selected_ids:

        try:
            if reference_image is not None:
                await reference_image.seek(0)

            response = await _run_source_search(
                source=selected_sources[source_id],
                reference_image=reference_image,
                text_prompt=text_prompt,
                search_mode=search_mode,
                frame_interval=frame_interval,
                min_detection_confidence=min_detection_confidence,
                max_results=max_results,
                recording_duration_seconds=recording_duration_seconds,
                db=db,
                owner_id=current_user.id,
                high_detail=high_detail,
            )

            child_result = response.get("result") or {}
            source_info = response.get("source") or {}

            search_id = child_result.get("search_id")

            if not search_id:
                raise RuntimeError(
                    "The source search returned no search ID."
                )

            source_entry = {
                "source_id": source_id,
                "source_name": source_info.get("name", source_id),
                "source_type": source_info.get("source_type", "unknown"),
                "status": "completed",
                "search_id": search_id,
                "match_count": len(child_result.get("matches") or []),
                "message": response.get(
                    "message",
                    "Search completed.",
                ),
            }

            source_results.append(source_entry)

            for match in child_result.get("matches") or []:
                combined_matches.append({
                    **match,
                    # Rank within the source's own search; the evidence
                    # viewer looks candidates up by this value.
                    "source_rank": match.get("rank"),
                    "source_id": source_id,
                    "source_name": source_entry["source_name"],
                    "source_type": source_entry["source_type"],
                    "search_id": search_id,
                })

        except Exception as error:

            if isinstance(error, HTTPException):
                message = str(error.detail)
            else:
                message = (
                    "The source search failed. Check the backend logs."
                )

            logger.warning(
                "Multi-source search %s: source %s failed: %s",
                multi_id,
                source_id,
                type(error).__name__,
            )

            source = selected_sources[source_id]

            source_results.append({
                "source_id": source_id,
                "source_name": source.name,
                "source_type": source.source_type,
                "status": "failed",
                "search_id": None,
                "match_count": 0,
                "message": message,
            })

    combined_matches.sort(
        key=lambda item: float(
            item.get(
                "ranking_score",
                item.get("similarity_score", 0),
            ) or 0
        ),
        reverse=True,
    )

    for rank, match in enumerate(combined_matches, start=1):
        match["rank"] = rank

    successful_count = sum(
        1 for item in source_results
        if item["status"] == "completed"
    )

    failed_count = len(source_results) - successful_count

    if successful_count == 0:
        overall_status = "failed"
    elif failed_count:
        overall_status = "partial"
    else:
        overall_status = "completed"

    created_at = utc_now()

    manifest = {
        "multi_search_id": multi_id,
        "owner_id": str(current_user.id),
        "status": overall_status,
        "created_at": created_at.isoformat(),
        "source_count": len(selected_ids),
        "successful_sources": successful_count,
        "failed_sources": failed_count,
        "settings": {
            "search_mode": search_mode,
            "text_prompt": text_prompt,
            "frame_interval": frame_interval,
            "min_detection_confidence": min_detection_confidence,
            "max_results_per_source": max_results,
            "recording_duration_seconds": recording_duration_seconds,
            "high_detail": high_detail,
        },
        "sources": source_results,
        "matches": combined_matches,
    }

    try:
        multi_record = MultiSourceSearch(
            id=multi_id,
            owner_id=current_user.id,
            status=overall_status,
            created_at=created_at,
            source_count=len(selected_ids),
            successful_sources=successful_count,
            failed_sources=failed_count,
            settings=manifest["settings"],
            matches_payload=combined_matches,
            original_payload=manifest,
        )

        db.add(multi_record)
        db.flush()

        for item in source_results:

            db.add(
                MultiSourceItem(
                    multi_search_id=multi_id,
                    source_id=item["source_id"],
                    search_id=item["search_id"],
                    source_name=item["source_name"],
                    source_type=item["source_type"],
                    status=item["status"],
                    match_count=item["match_count"],
                    message=item["message"],
                    original_payload=item,
                )
            )

        db.commit()

    except SQLAlchemyError as error:
        db.rollback()

        logger.exception("Multi-source database save failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to save the multi-source search to the database.",
        ) from error

    return {
        "status": overall_status,
        "message": (
            f"Multi-source search finished: {successful_count} source(s) "
            f"succeeded and {failed_count} failed."
        ),
        "multi_search_id": multi_id,
        "result": manifest,
    }
