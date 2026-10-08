import os
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.search_service import search_service


router = APIRouter(
    prefix="/api/search",
    tags=["Search"],
)


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(CURRENT_DIR)
    )
)

UPLOADS_DIR = os.path.join(BACKEND_DIR, "uploads")

os.makedirs(UPLOADS_DIR, exist_ok=True)


# ---------------------------------------------------------
# Helper: save uploaded file
# ---------------------------------------------------------

def save_uploaded_file(
    upload_file: UploadFile,
    destination_folder: str,
) -> str:

    os.makedirs(destination_folder, exist_ok=True)

    original_name = upload_file.filename or "uploaded_file"

    extension = os.path.splitext(original_name)[1]

    unique_name = f"{uuid.uuid4().hex}{extension}"

    file_path = os.path.join(
        destination_folder,
        unique_name,
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            upload_file.file,
            buffer,
        )

    return file_path


# ---------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------

@router.post("")
async def search_object(
    reference_image: UploadFile = File(...),
    video: UploadFile = File(...),
    frame_interval: int = Form(5),
    min_detection_confidence: float = Form(0.25),
    max_results: int = Form(20),
):
    """
    Upload a reference image and video, then search the
    video for visually similar objects.
    """

    # -----------------------------------------------------
    # Validate reference image
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Validate video
    # -----------------------------------------------------

    if not video.content_type:
        raise HTTPException(
            status_code=400,
            detail="Video content type is missing.",
        )

    if not video.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be a video.",
        )

    # -----------------------------------------------------
    # Validate parameters
    # -----------------------------------------------------

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

    if max_results < 1:
        raise HTTPException(
            status_code=400,
            detail="max_results must be at least 1.",
        )

    # -----------------------------------------------------
    # Create request folder
    # -----------------------------------------------------

    request_id = uuid.uuid4().hex

    request_folder = os.path.join(
        UPLOADS_DIR,
        request_id,
    )

    os.makedirs(request_folder, exist_ok=True)

    try:

        # -------------------------------------------------
        # Save reference image
        # -------------------------------------------------

        reference_path = save_uploaded_file(
            reference_image,
            request_folder,
        )

        # -------------------------------------------------
        # Save video
        # -------------------------------------------------

        video_path = save_uploaded_file(
            video,
            request_folder,
        )

        print("\n" + "=" * 60)
        print("NEW VISIONTRACE SEARCH REQUEST")
        print("=" * 60)

        print(f"Request ID      : {request_id}")
        print(f"Reference image : {reference_path}")
        print(f"Video           : {video_path}")

        # -------------------------------------------------
        # Run ML search
        # -------------------------------------------------

        result = search_service.run_search(
            reference_image=reference_path,
            video_path=video_path,
            frame_interval=frame_interval,
            min_detection_confidence=min_detection_confidence,
            max_results=max_results,
        )

        # -------------------------------------------------
        # Return result
        # -------------------------------------------------

        return {
            "status": "completed",
            "message": "VisionTrace search completed successfully.",
            "request_id": request_id,
            "result": result,
        }

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception as error:

        print("\nVISIONTRACE SEARCH ERROR")
        print(str(error))

        raise HTTPException(
            status_code=500,
            detail=f"VisionTrace search failed: {str(error)}",
        )