import os
import sys
from typing import Any, Dict

# ---------------------------------------------------------
# Locate the VisionTrace ML Engine
# ---------------------------------------------------------

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))

PROJECT_DIR = os.path.dirname(BACKEND_DIR)

ML_ENGINE_DIR = os.path.join(PROJECT_DIR, "ml-engene")

if ML_ENGINE_DIR not in sys.path:
    sys.path.insert(0, ML_ENGINE_DIR)


# ---------------------------------------------------------
# Import VisionTrace ML Pipeline
# ---------------------------------------------------------

from pipeline.search_pipeline import VisionTracePipeline


class SearchService:
    """
    Service responsible for connecting the FastAPI backend
    to the VisionTrace AI machine-learning pipeline.
    """

    def __init__(self):
        self.pipeline = None

    def _get_pipeline(self) -> VisionTracePipeline:
        """
        Load the ML pipeline only when it is needed.

        This prevents the YOLO and DINOv2 models from being
        loaded every time the backend starts.
        """

        if self.pipeline is None:
            print("Initializing VisionTrace ML pipeline...")
            self.pipeline = VisionTracePipeline()
            print("VisionTrace ML pipeline initialized.")

        return self.pipeline

    def run_search(
        self,
        reference_image: str,
        video_path: str,
        frame_interval: int = 5,
        min_detection_confidence: float = 0.25,
        max_results: int = 20,
    ) -> Dict[str, Any]:
        """
        Run an object search using the VisionTrace ML pipeline.
        """

        if not os.path.exists(reference_image):
            raise FileNotFoundError(
                f"Reference image not found: {reference_image}"
            )

        if not os.path.exists(video_path):
            raise FileNotFoundError(
                f"Video file not found: {video_path}"
            )

        pipeline = self._get_pipeline()

        print("=" * 60)
        print("VISIONTRACE AI BACKEND SEARCH")
        print("=" * 60)

        print(f"Reference image : {reference_image}")
        print(f"Video           : {video_path}")
        print(f"Frame interval  : {frame_interval}")
        print(f"Min confidence  : {min_detection_confidence}")
        print(f"Maximum results : {max_results}")

        result = pipeline.search(
            reference_image=reference_image,
            video_path=video_path,
            frame_interval=frame_interval,
            min_detection_confidence=min_detection_confidence,
            max_results=max_results,
        )

        print("=" * 60)
        print("VISIONTRACE AI BACKEND SEARCH COMPLETE")
        print("=" * 60)

        return result


# ---------------------------------------------------------
# Shared service instance
# ---------------------------------------------------------

search_service = SearchService()