import json
import mimetypes
import os
from typing import Any, Dict, List, Iterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, Response

router = APIRouter(
    prefix="/api/search",
    tags=["Results"],
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(CURRENT_DIR)
    )
)

RESULTS_DIR = os.path.join(BACKEND_DIR, "results")
UPLOADS_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "uploads"))


def get_search_folder(search_id: str) -> str:
    # Reject path separators so a search ID cannot escape RESULTS_DIR.
    if (
        not search_id
        or "/" in search_id
        or "\\" in search_id
        or search_id in {".", ".."}
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid search ID.",
        )

    search_folder = os.path.join(RESULTS_DIR, search_id)

    if not os.path.isdir(search_folder):
        raise HTTPException(
            status_code=404,
            detail=f"Search not found: {search_id}",
        )

    return search_folder


def load_result_file(search_folder: str) -> Dict[str, Any]:
    result_file = os.path.join(search_folder, "result.json")

    if not os.path.isfile(result_file):
        raise HTTPException(
            status_code=404,
            detail="Result file not found.",
        )

    try:
        with open(result_file, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="The result file contains invalid JSON.",
        )
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read search result: {error}",
        )


def get_original_video_path(search_id: str) -> str:
    search_folder = get_search_folder(search_id)
    result = load_result_file(search_folder)

    video_info = result.get("video") or {}
    video_path = video_info.get("path")

    if not video_path or not isinstance(video_path, str):
        raise HTTPException(
            status_code=404,
            detail="The original video path is not available for this search.",
        )

    if not os.path.isabs(video_path):
        video_path = os.path.join(BACKEND_DIR, video_path)

    video_path = os.path.abspath(video_path)

    # Only serve videos stored inside this application's uploads directory.
    try:
        common_path = os.path.commonpath(
            [os.path.normcase(UPLOADS_DIR), os.path.normcase(video_path)]
        )
    except ValueError:
        common_path = ""

    if common_path != os.path.normcase(UPLOADS_DIR):
        raise HTTPException(
            status_code=403,
            detail="The requested video is outside the permitted uploads directory.",
        )

    if not os.path.isfile(video_path):
        raise HTTPException(
            status_code=404,
            detail="The original uploaded video could not be found.",
        )

    return video_path


def iter_file_range(
    file_path: str,
    start: int,
    end: int,
    chunk_size: int = 1024 * 1024,
) -> Iterator[bytes]:
    """Stream a file range without loading the whole video into memory."""
    remaining = end - start + 1

    with open(file_path, "rb") as file:
        file.seek(start)

        while remaining > 0:
            chunk = file.read(min(chunk_size, remaining))

            if not chunk:
                break

            remaining -= len(chunk)
            yield chunk


def parse_byte_range(
    range_header: str,
    file_size: int,
):
    """
    Parse a single HTTP byte range.
    Returns (start, end), or raises ValueError for an invalid range.
    """
    if not range_header.startswith("bytes="):
        raise ValueError("Unsupported range unit.")

    range_value = range_header[len("bytes="):].strip()

    # This endpoint supports one range at a time.
    if "," in range_value or "-" not in range_value or file_size <= 0:
        raise ValueError("Invalid byte range.")

    start_text, end_text = range_value.split("-", 1)

    if start_text == "":
        # Suffix range, e.g. bytes=-500
        try:
            suffix_length = int(end_text)
        except ValueError:
            raise ValueError("Invalid suffix range.")

        if suffix_length <= 0:
            raise ValueError("Invalid suffix length.")

        start = max(file_size - suffix_length, 0)
        end = file_size - 1
    else:
        try:
            start = int(start_text)
        except ValueError:
            raise ValueError("Invalid range start.")

        if start < 0 or start >= file_size:
            raise ValueError("Range start is outside the file.")

        if end_text == "":
            end = file_size - 1
        else:
            try:
                end = int(end_text)
            except ValueError:
                raise ValueError("Invalid range end.")

            if end < start:
                raise ValueError("Range end is before range start.")

            end = min(end, file_size - 1)

    return start, end


@router.get("")
def get_search_history() -> List[Dict[str, Any]]:
    if not os.path.isdir(RESULTS_DIR):
        return []

    searches = []

    for search_id in os.listdir(RESULTS_DIR):
        search_folder = os.path.join(RESULTS_DIR, search_id)

        if not os.path.isdir(search_folder):
            continue

        result_file = os.path.join(search_folder, "result.json")

        if not os.path.isfile(result_file):
            continue

        try:
            with open(result_file, "r", encoding="utf-8") as file:
                result = json.load(file)
        except (json.JSONDecodeError, OSError):
            continue

        matches = result.get("matches", [])
        search_info = result.get("search", {})
        video_info = result.get("video", {})

        top_match = matches[0] if matches else None

        searches.append(
            {
                "search_id": result.get("search_id", search_id),
                "status": result.get("status", "unknown"),
                "created_at": result.get("created_at"),
                "video": {
                    "duration": video_info.get("duration", 0),
                    "fps": video_info.get("fps", 0),
                    "frame_count": video_info.get("frame_count", 0),
                    "width": video_info.get("width", 0),
                    "height": video_info.get("height", 0),
                },
                "search": {
                    "frames_analyzed": search_info.get("frames_analyzed", 0),
                    "candidate_observations": search_info.get(
                        "candidate_observations", 0
                    ),
                    "unique_tracks": search_info.get("unique_tracks", 0),
                    "candidates": search_info.get("candidates", 0),
                },
                "top_match": (
                    {
                        "rank": top_match.get("rank"),
                        "track_id": top_match.get("track_id"),
                        "class_name": top_match.get("class_name"),
                        "match_status": top_match.get("match_status"),
                        "similarity_score": top_match.get("similarity_score"),
                        "ranking_score": top_match.get("ranking_score"),
                        "timestamp": top_match.get("timestamp"),
                    }
                    if top_match
                    else None
                ),
            }
        )

    searches.sort(
        key=lambda item: item.get("created_at") or "",
        reverse=True,
    )

    return searches


@router.get("/{search_id}")
def get_search_result(search_id: str):
    search_folder = get_search_folder(search_id)
    return load_result_file(search_folder)


@router.get("/{search_id}/summary")
def get_search_summary(search_id: str):
    search_folder = get_search_folder(search_id)
    summary_file = os.path.join(search_folder, "summary.json")

    if not os.path.isfile(summary_file):
        raise HTTPException(
            status_code=404,
            detail="Summary file not found.",
        )

    try:
        with open(summary_file, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="The summary file contains invalid JSON.",
        )


@router.get("/{search_id}/video")
def get_search_video(
    search_id: str,
    request: Request,
):
    """
    Stream the original video for a completed search.
    Supports HTTP Range requests so browser playback can seek.
    """
    video_path = get_original_video_path(search_id)
    file_size = os.path.getsize(video_path)

    media_type, _ = mimetypes.guess_type(video_path)
    if not media_type:
        media_type = "application/octet-stream"

    range_header = request.headers.get("range")

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": (
            f'inline; filename="{os.path.basename(video_path)}"'
        ),
        "Cache-Control": "no-store",
    }

    if not range_header:
        headers["Content-Length"] = str(file_size)

        return StreamingResponse(
            iter_file_range(video_path, 0, max(file_size - 1, -1)),
            media_type=media_type,
            headers=headers,
            status_code=200,
        )

    try:
        start, end = parse_byte_range(range_header, file_size)
    except ValueError:
        return Response(
            status_code=416,
            headers={
                "Content-Range": f"bytes */{file_size}",
                "Accept-Ranges": "bytes",
            },
        )

    content_length = end - start + 1

    headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    headers["Content-Length"] = str(content_length)

    return StreamingResponse(
        iter_file_range(video_path, start, end),
        status_code=206,
        media_type=media_type,
        headers=headers,
    )


@router.get("/{search_id}/evidence/{filename}")
def get_evidence(
    search_id: str,
    filename: str,
):
    search_folder = get_search_folder(search_id)

    evidence_folder = os.path.join(search_folder, "evidence")
    file_path = os.path.abspath(os.path.join(evidence_folder, filename))
    evidence_root = os.path.abspath(evidence_folder)

    try:
        common_path = os.path.commonpath(
            [os.path.normcase(evidence_root), os.path.normcase(file_path)]
        )
    except ValueError:
        common_path = ""

    if common_path != os.path.normcase(evidence_root):
        raise HTTPException(
            status_code=400,
            detail="Invalid evidence file path.",
        )

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=404,
            detail="Evidence file not found.",
        )

    return FileResponse(
        file_path,
        media_type="image/jpeg",
        filename=os.path.basename(file_path),
    )