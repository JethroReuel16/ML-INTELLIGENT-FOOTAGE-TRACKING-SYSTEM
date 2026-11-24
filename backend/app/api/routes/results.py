import logging
import mimetypes
import os
import shutil
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    SearchRecord,
    SearchMatch,
    MultiSourceSearch,
    EvidenceFile,
    VideoSource,
)
from app.storage import (
    ALLOWED_RESULTS_DIRS,
    ALLOWED_UPLOADS_DIRS,
    resolve_inside,
)
from app.api.routes.auth import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Results"])


def source_summary(source):
    """Public description of the video source a search ran on."""
    if source is None:
        return None
    return {
        "id": source.id,
        "name": source.name,
        "source_type": source.source_type,
        "location": source.location,
    }


def owner_sources(db, owner_id):
    """All of a user's sources keyed by id (one query instead of one per search)."""
    return {
        source.id: source
        for source in db.query(VideoSource).filter(VideoSource.owner_id == owner_id)
    }


# ---------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------

def to_iso(value):
    if value is None:
        return None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return str(value)


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def safe_int(value, default=0):
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def resolve_evidence_path(stored_path):
    if not stored_path:
        return None

    candidates = []

    stored_path = os.path.expanduser(str(stored_path))

    if os.path.isabs(stored_path):
        candidates.append(stored_path)
    else:
        for directory in ALLOWED_RESULTS_DIRS:
            candidates.append(
                os.path.join(directory, stored_path)
            )

    for candidate in candidates:
        resolved = resolve_inside(
            candidate,
            ALLOWED_RESULTS_DIRS,
        )

        if resolved and os.path.isfile(resolved):
            return resolved

    return None


def match_to_dict(match):
    original = as_dict(match.original_payload)

    return {
        "rank": original.get("rank", match.rank),
        "track_id": original.get("track_id", match.track_id),
        "class_id": original.get("class_id", match.class_id),
        "class_name": original.get("class_name", match.class_name),
        "match_status": original.get(
            "match_status", match.match_status
        ),
        "similarity_score": original.get(
            "similarity_score", match.similarity_score
        ),
        "ranking_score": original.get(
            "ranking_score", match.ranking_score
        ),
        "top3_average": original.get(
            "top3_average", match.top3_average
        ),
        "average_similarity": original.get(
            "average_similarity", match.average_similarity
        ),
        "timestamp": original.get("timestamp", match.timestamp),
        "frame_number": original.get(
            "frame_number", match.frame_number
        ),
        "bbox": original.get("bbox", match.bbox),
        "detection_confidence": original.get(
            "detection_confidence", match.detection_confidence
        ),
        "frames_observed": original.get(
            "frames_observed", match.frames_observed
        ),
        "evidence_image": original.get(
            "evidence_image", match.evidence_image
        ),
    }


def get_search_record(db, search_id, user_id):
    record = (
        db.query(SearchRecord)
        .filter(
            SearchRecord.id == search_id,
            SearchRecord.owner_id == user_id,
        )
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Search not found.",
        )

    return record


def get_search_result_payload(db, record):
    payload = as_dict(record.result_payload)
    source = (
        source_summary(db.get(VideoSource, record.source_id))
        if record.source_id
        else None
    )

    if payload:
        result = dict(payload)
        result["search_id"] = record.id
        result["source"] = source
        # Internal server paths are not useful to (or safe for) clients.
        result.pop("files", None)

        if not result.get("created_at"):
            result["created_at"] = to_iso(record.created_at)

        return result

    matches = (
        db.query(SearchMatch)
        .filter(SearchMatch.search_id == record.id)
        .order_by(SearchMatch.rank.asc())
        .all()
    )

    return {
        "status": record.status,
        "search_id": record.id,
        "created_at": to_iso(record.created_at),
        "reference": as_dict(record.reference_data),
        "video": as_dict(record.video_metadata),
        "search": as_dict(record.search_settings),
        "matches": [match_to_dict(item) for item in matches],
        "source": source,
    }


# ---------------------------------------------------------
# SEARCH HISTORY
# GET /api/search
# ---------------------------------------------------------

@router.get("")
def get_search_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    records = (
        db.query(SearchRecord)
        .filter(SearchRecord.owner_id == current_user.id)
        .order_by(
            SearchRecord.imported_at.desc(),
            SearchRecord.id.desc(),
        )
        .all()
    )

    sources = owner_sources(db, current_user.id)
    history = []

    for record in records:
        summary = as_dict(record.summary_payload)
        video = as_dict(
            summary.get("video") or record.video_metadata
        )
        search = as_dict(
            summary.get("search") or record.search_settings
        )

        top_match = summary.get("top_match")

        if not isinstance(top_match, dict):
            first_match = (
                db.query(SearchMatch)
                .filter(SearchMatch.search_id == record.id)
                .order_by(SearchMatch.rank.asc())
                .first()
            )

            top_match = (
                match_to_dict(first_match)
                if first_match
                else None
            )

        if top_match:
            top_match = {
                "rank": top_match.get("rank"),
                "track_id": top_match.get("track_id"),
                "class_name": top_match.get("class_name"),
                "match_status": top_match.get("match_status"),
                "similarity_score": top_match.get(
                    "similarity_score"
                ),
                "ranking_score": top_match.get("ranking_score"),
                "ranking_basis": top_match.get("ranking_basis"),
                "timestamp": top_match.get("timestamp"),
            }

        history.append({
            "search_id": record.id,
            "status": record.status,
            "created_at": (
                to_iso(record.created_at)
                or to_iso(record.imported_at)
            ),
            "video": {
                "duration": safe_float(video.get("duration")),
                "fps": safe_float(video.get("fps")),
                "frame_count": safe_int(
                    video.get("frame_count")
                ),
                "width": safe_int(video.get("width")),
                "height": safe_int(video.get("height")),
            },
            "search": {
                "frames_analyzed": safe_int(
                    search.get("frames_analyzed")
                ),
                "candidate_observations": safe_int(
                    search.get("candidate_observations")
                ),
                "unique_tracks": safe_int(
                    search.get("unique_tracks")
                ),
                "candidates": safe_int(
                    search.get("candidates")
                ),
                "search_mode": search.get("search_mode") or "image",
                "text_prompt": search.get("text_prompt"),
            },
            "top_match": top_match,
            "source": source_summary(sources.get(record.source_id)),
        })

    return history


# ---------------------------------------------------------
# MULTI-SOURCE SEARCH LIST
# GET /api/search/multi
# ---------------------------------------------------------

@router.get("/multi")
def list_multi_source_searches(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    records = (
        db.query(MultiSourceSearch)
        .filter(MultiSourceSearch.owner_id == current_user.id)
        .order_by(MultiSourceSearch.created_at.desc().nullslast())
        .all()
    )

    items = []

    for record in records:
        settings = as_dict(record.settings)
        matches = as_list(record.matches_payload)
        top = next((m for m in matches if isinstance(m, dict)), None)

        items.append({
            "multi_search_id": record.id,
            "status": record.status,
            "created_at": to_iso(record.created_at) or to_iso(record.imported_at),
            "source_count": safe_int(record.source_count),
            "successful_sources": safe_int(record.successful_sources),
            "failed_sources": safe_int(record.failed_sources),
            "match_count": len(matches),
            "search_mode": settings.get("search_mode") or "image",
            "text_prompt": settings.get("text_prompt"),
            "source_names": [item.source_name for item in record.items if item.source_name],
            "top_match": (
                {
                    "class_name": top.get("class_name"),
                    "source_name": top.get("source_name"),
                    "similarity_score": top.get("similarity_score"),
                    "ranking_score": top.get("ranking_score"),
                    "timestamp": top.get("timestamp"),
                }
                if top
                else None
            ),
        })

    return items


# ---------------------------------------------------------
# MULTI-SOURCE SEARCH RESULT
# GET /api/search/multi/{multi_search_id}
# ---------------------------------------------------------

@router.get("/multi/{multi_search_id}")
def get_multi_source_result(
    multi_search_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = (
        db.query(MultiSourceSearch)
        .filter(
            MultiSourceSearch.id == multi_search_id,
            MultiSourceSearch.owner_id == current_user.id,
        )
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Multi-source search not found.",
        )

    manifest = as_dict(record.original_payload)
    settings = as_dict(
        record.settings or manifest.get("settings")
    )

    matches = as_list(record.matches_payload)

    sources = []

    for item in record.items:
        sources.append({
            "source_id": item.source_id,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "status": item.status,
            # NULL once the per-source search has been deleted.
            "search_id": item.search_id,
            "match_count": safe_int(item.match_count),
            "message": item.message,
        })

    existing_search_ids = {
        row[0]
        for row in db.query(SearchRecord.id).filter(
            SearchRecord.id.in_(
                {m.get("search_id") for m in matches if isinstance(m, dict)}
            )
        )
    }

    normalized_matches = []

    for match in matches:
        if not isinstance(match, dict):
            continue

        if match.get("search_id") not in existing_search_ids:
            continue  # its source search was deleted

        match = dict(match)

        # Searches saved before "source_rank" existed overwrote "rank" with
        # the global rank. Recover the per-source rank from the stored match.
        if match.get("source_rank") is None and match.get("search_id"):
            stored = (
                db.query(SearchMatch.rank)
                .filter(
                    SearchMatch.search_id == match["search_id"],
                    SearchMatch.track_id == match.get("track_id"),
                )
                .order_by(SearchMatch.rank.asc())
                .first()
            )
            match["source_rank"] = stored[0] if stored else match.get("rank")

        normalized_matches.append(match)

    return {
        "multi_search_id": record.id,
        "status": record.status,
        "created_at": (
            to_iso(record.created_at)
            or to_iso(record.imported_at)
        ),
        "source_count": safe_int(record.source_count),
        "successful_sources": safe_int(
            record.successful_sources
        ),
        "failed_sources": safe_int(record.failed_sources),
        "settings": {
            "search_mode": settings.get("search_mode") or "image",
            "text_prompt": settings.get("text_prompt"),
            "frame_interval": safe_int(
                settings.get("frame_interval")
            ),
            "min_detection_confidence": safe_float(
                settings.get("min_detection_confidence")
            ),
            "max_results_per_source": safe_int(
                settings.get("max_results_per_source")
            ),
            "recording_duration_seconds": safe_int(
                settings.get("recording_duration_seconds")
            ),
        },
        "sources": sources,
        "matches": normalized_matches,
    }


# ---------------------------------------------------------
# SEARCH SUMMARY
# GET /api/search/{search_id}/summary
# ---------------------------------------------------------

@router.get("/{search_id}/summary")
def get_search_summary(
    search_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = get_search_record(
        db,
        search_id,
        current_user.id,
    )

    summary = as_dict(record.summary_payload)

    if summary:
        return summary

    result = get_search_result_payload(db, record)
    matches = as_list(result.get("matches"))

    return {
        "status": record.status,
        "search_id": record.id,
        "owner_id": str(current_user.id),
        "created_at": to_iso(record.created_at),
        "video": as_dict(result.get("video")),
        "search": as_dict(result.get("search")),
        "top_match": matches[0] if matches else None,
    }


# ---------------------------------------------------------
# EVIDENCE IMAGE
# GET /api/search/{search_id}/evidence/{filename}
# ---------------------------------------------------------

@router.get("/{search_id}/evidence/{filename}")
def get_search_evidence(
    search_id: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = get_search_record(
        db,
        search_id,
        current_user.id,
    )

    requested_filename = os.path.basename(filename)

    if requested_filename != filename or filename in ("", ".", ".."):
        raise HTTPException(
            status_code=400,
            detail="Invalid evidence filename.",
        )

    evidence_records = (
        db.query(EvidenceFile)
        .filter(EvidenceFile.search_id == record.id)
        .all()
    )

    for evidence in evidence_records:
        stored_path = str(evidence.file_path or "")

        if os.path.basename(stored_path) != requested_filename:
            continue

        resolved = resolve_evidence_path(stored_path)

        if not resolved:
            continue

        media_type = (
            mimetypes.guess_type(resolved)[0]
            or "application/octet-stream"
        )

        return FileResponse(
            path=resolved,
            media_type=media_type,
            filename=requested_filename,
        )

    raise HTTPException(
        status_code=404,
        detail="Evidence image not found.",
    )


# ---------------------------------------------------------
# ORIGINAL FOOTAGE
# GET /api/search/{search_id}/video
# ---------------------------------------------------------

@router.get("/{search_id}/video")
def get_search_video(
    search_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Stream the footage a search was run on. Supports HTTP Range requests,
    so browsers can seek without downloading the whole file.
    """

    record = get_search_record(
        db,
        search_id,
        current_user.id,
    )

    stored_path = record.video_path or as_dict(record.video_metadata).get("path")

    # Only files inside the uploads area may be served.
    resolved = resolve_inside(stored_path, ALLOWED_UPLOADS_DIRS)

    if not resolved or not os.path.isfile(resolved):
        raise HTTPException(
            status_code=404,
            detail="The original footage for this search is no longer available.",
        )

    media_type = mimetypes.guess_type(resolved)[0] or "video/mp4"

    return FileResponse(
        path=resolved,
        media_type=media_type,
        content_disposition_type="inline",
        filename=os.path.basename(resolved),
    )


# ---------------------------------------------------------
# DELETE A SEARCH
# DELETE /api/search/{search_id}
# ---------------------------------------------------------

def _search_folders(record):
    """Evidence and footage folders of a search, verified to be inside storage."""
    folders = []

    result_folder = as_dict(as_dict(record.result_payload).get("files")).get("search_folder")
    if not result_folder:
        first_evidence = next(
            (m.evidence_image for m in record.matches if m.evidence_image), None
        )
        if first_evidence:
            # .../results/<search_id>/evidence/<file>.jpg
            result_folder = os.path.dirname(os.path.dirname(first_evidence))

    resolved = resolve_inside(result_folder, ALLOWED_RESULTS_DIRS)
    if resolved and resolved not in ALLOWED_RESULTS_DIRS:
        folders.append(resolved)

    if record.video_path:
        upload_folder = resolve_inside(os.path.dirname(record.video_path), ALLOWED_UPLOADS_DIRS)
        if upload_folder and upload_folder not in ALLOWED_UPLOADS_DIRS:
            folders.append(upload_folder)

    return folders


@router.delete("/{search_id}")
def delete_search(
    search_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a search with its matches, evidence images and stored footage."""

    record = get_search_record(db, search_id, current_user.id)
    folders = _search_folders(record)

    db.query(EvidenceFile).filter(EvidenceFile.search_id == record.id).delete(
        synchronize_session=False
    )
    db.delete(record)
    db.commit()

    # Files go after the commit: a failed delete never leaves a record
    # pointing at missing evidence.
    for folder in folders:
        shutil.rmtree(folder, ignore_errors=True)

    logger.info("Search %s deleted by user %s", search_id, current_user.id)

    return {"message": "Search deleted.", "search_id": search_id}


# ---------------------------------------------------------
# INDIVIDUAL SEARCH RESULT
# GET /api/search/{search_id}
# ---------------------------------------------------------

@router.get("/{search_id}")
def get_search_result(
    search_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = get_search_record(
        db,
        search_id,
        current_user.id,
    )

    return get_search_result_payload(db, record)
