
import logging
import os
import sys
import threading
import time
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

ML_ENGINE_DIR = settings.ml_engine_dir

if ML_ENGINE_DIR not in sys.path:
    # Append (not prepend): the ML engine has its own main.py and tests/
    # package, which must not shadow the backend's modules.
    sys.path.append(ML_ENGINE_DIR)

from app.storage import DEBUG_CROPS_DIR, RESULTS_DIR
from detection.base import DetectorCapabilityError
from ml_config import parse_text_prompts
from pipeline.search_pipeline import (
    VisionTracePipeline,
    resolve_search_mode,
)
from video.processor import VideoReadError


class SearchService:
    def __init__(self):
        self.pipeline = None
        # Serialises model loading: two searches arriving together on a
        # fresh server must not load the (large) models twice.
        self._init_lock = threading.Lock()
        self.state = "not_loaded"  # not_loaded | loading | ready | error
        self.error = None

    def _get_pipeline(self):
        if self.pipeline is not None:
            return self.pipeline

        with self._init_lock:
            if self.pipeline is None:
                self.state, self.error = "loading", None
                started = time.monotonic()
                logger.info("Loading ML models...")
                try:
                    self.pipeline = VisionTracePipeline(
                        debug_folder=DEBUG_CROPS_DIR,
                        results_folder=RESULTS_DIR,
                    )
                except Exception as error:
                    self.state, self.error = "error", f"{type(error).__name__}: {error}"
                    logger.exception("ML models failed to load")
                    raise
                self.state = "ready"
                logger.info("ML models ready in %.1fs.", time.monotonic() - started)

        return self.pipeline

    def preload_in_background(self) -> None:
        """Load the models at start-up so the first search does not wait."""

        def load():
            try:
                self._get_pipeline()
            except Exception:
                pass  # already logged; the next search retries

        threading.Thread(target=load, name="ml-preload", daemon=True).start()

    def status(self) -> Dict[str, Any]:
        """Model state without triggering a load (for health checks)."""
        info = {"state": self.state}
        if self.error:
            info["error"] = self.error
        if self.pipeline is not None:
            info["detector"] = self.pipeline.detector_status.get("active")
            info["device"] = self.pipeline.detector_status.get("device")
            info["fallback"] = bool(self.pipeline.detector_status.get("fallback"))
        return info

    def detector_status(self) -> Dict[str, Any]:
        """Active detector and fallback status (loads the pipeline)."""
        return dict(self._get_pipeline().detector_status)

    def run_search(
        self,
        video_path: str,
        reference_image: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Run an image, text, or image + text search.

        kwargs may include text_prompt, search_mode, frame_interval,
        min_detection_confidence, max_results and owner_id.
        """

        if reference_image and not os.path.isfile(reference_image):
            raise FileNotFoundError(
                f"Reference image not found: {reference_image}"
            )

        if not video_path or not os.path.isfile(video_path):
            raise FileNotFoundError(
                f"Video file not found: {video_path}"
            )

        pipeline = self._get_pipeline()

        return pipeline.search(
            reference_image=reference_image,
            video_path=video_path,
            **kwargs,
        )


# Shared application instance used by the API routes.
search_service = SearchService()


__all__ = [
    "search_service",
    "DetectorCapabilityError",
    "VideoReadError",
    "parse_text_prompts",
    "resolve_search_mode",
]
