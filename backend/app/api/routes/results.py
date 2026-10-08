import json
import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter(
    prefix="/api/search",
    tags=["Results"],
)


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# CURRENT_DIR:
# J:\visiontarce\backend\app\api\routes
#
# Move up:
# routes -> api -> app -> backend
BACKEND_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(CURRENT_DIR)
    )
)


# VisionTrace backend results directory.
#
# The ML pipeline currently creates:
#
# J:\visiontarce\backend\results\
#
RESULTS_DIR = os.path.join(
    BACKEND_DIR,
    "results",
)


def get_search_folder(search_id: str) -> str:
    """
    Return the folder containing a specific search result.
    """

    search_folder = os.path.join(
        RESULTS_DIR,
        search_id,
    )

    if not os.path.isdir(search_folder):
        raise HTTPException(
            status_code=404,
            detail=f"Search not found: {search_id}",
        )

    return search_folder


def load_result_file(
    search_folder: str,
) -> Dict[str, Any]:
    """
    Load result.json from a search folder.
    """

    result_file = os.path.join(
        search_folder,
        "result.json",
    )

    if not os.path.isfile(result_file):
        raise HTTPException(
            status_code=404,
            detail="Result file not found.",
        )

    try:
        with open(
            result_file,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="The result file contains invalid JSON.",
        )


# ============================================================
# SEARCH HISTORY
# ============================================================

@router.get("")
def get_search_history() -> List[Dict[str, Any]]:
    """
    Return a summary of all completed VisionTrace searches.

    Each search is read from the result.json file stored inside
    the backend results directory.
    """

    if not os.path.isdir(RESULTS_DIR):
        return []

    searches = []

    for search_id in os.listdir(RESULTS_DIR):

        search_folder = os.path.join(
            RESULTS_DIR,
            search_id,
        )

        # Ignore files and unexpected entries.
        if not os.path.isdir(search_folder):
            continue

        result_file = os.path.join(
            search_folder,
            "result.json",
        )

        # Ignore folders that do not contain result.json.
        if not os.path.isfile(result_file):
            continue

        try:
            with open(
                result_file,
                "r",
                encoding="utf-8",
            ) as file:
                result = json.load(file)

        except (json.JSONDecodeError, OSError):
            # Do not allow one broken result to prevent
            # the entire history from loading.
            continue

        matches = result.get(
            "matches",
            [],
        )

        search_info = result.get(
            "search",
            {}
        )

        video_info = result.get(
            "video",
            {}
        )

        top_match = (
            matches[0]
            if matches
            else None
        )

        searches.append(
            {
                "search_id": result.get(
                    "search_id",
                    search_id,
                ),
                "status": result.get(
                    "status",
                    "unknown",
                ),
                "created_at": result.get(
                    "created_at",
                ),

                "video": {
                    "duration": video_info.get(
                        "duration",
                        0,
                    ),
                    "fps": video_info.get(
                        "fps",
                        0,
                    ),
                    "frame_count": video_info.get(
                        "frame_count",
                        0,
                    ),
                    "width": video_info.get(
                        "width",
                        0,
                    ),
                    "height": video_info.get(
                        "height",
                        0,
                    ),
                },

                "search": {
                    "frames_analyzed": search_info.get(
                        "frames_analyzed",
                        0,
                    ),
                    "candidate_observations": search_info.get(
                        "candidate_observations",
                        0,
                    ),
                    "unique_tracks": search_info.get(
                        "unique_tracks",
                        0,
                    ),
                    "candidates": search_info.get(
                        "candidates",
                        0,
                    ),
                },

                "top_match": (
                    {
                        "rank": top_match.get(
                            "rank",
                        ),
                        "track_id": top_match.get(
                            "track_id",
                        ),
                        "class_name": top_match.get(
                            "class_name",
                        ),
                        "match_status": top_match.get(
                            "match_status",
                        ),
                        "similarity_score": top_match.get(
                            "similarity_score",
                        ),
                        "ranking_score": top_match.get(
                            "ranking_score",
                        ),
                        "timestamp": top_match.get(
                            "timestamp",
                        ),
                    }
                    if top_match
                    else None
                ),
            }
        )

    # Newest searches first.
    searches.sort(
        key=lambda item: item.get(
            "created_at"
        ) or "",
        reverse=True,
    )

    return searches


# ============================================================
# SPECIFIC SEARCH RESULT
# ============================================================

@router.get("/{search_id}")
def get_search_result(
    search_id: str,
):
    """
    Return the complete result for one search.
    """

    search_folder = get_search_folder(
        search_id
    )

    result = load_result_file(
        search_folder
    )

    return result


# ============================================================
# SEARCH SUMMARY
# ============================================================

@router.get("/{search_id}/summary")
def get_search_summary(
    search_id: str,
):
    """
    Return the summary.json file for one search.
    """

    search_folder = get_search_folder(
        search_id
    )

    summary_file = os.path.join(
        search_folder,
        "summary.json",
    )

    if not os.path.isfile(summary_file):
        raise HTTPException(
            status_code=404,
            detail="Summary file not found.",
        )

    try:
        with open(
            summary_file,
            "r",
            encoding="utf-8",
        ) as file:
            summary = json.load(file)

        return summary

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="The summary file contains invalid JSON.",
        )


# ============================================================
# EVIDENCE IMAGE
# ============================================================

@router.get("/{search_id}/evidence/{filename}")
def get_evidence(
    search_id: str,
    filename: str,
):
    """
    Return an evidence image for a specific search.
    """

    search_folder = get_search_folder(
        search_id
    )

    evidence_folder = os.path.join(
        search_folder,
        "evidence",
    )

    file_path = os.path.join(
        evidence_folder,
        filename,
    )

    evidence_root = os.path.abspath(
        evidence_folder
    )

    requested_file = os.path.abspath(
        file_path
    )

    # Prevent directory traversal.
    if not requested_file.startswith(
        evidence_root + os.sep
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid evidence file path.",
        )

    if not os.path.isfile(
        requested_file
    ):
        raise HTTPException(
            status_code=404,
            detail="Evidence file not found.",
        )

    return FileResponse(
        requested_file,
        media_type="image/jpeg",
        filename=filename,
    )