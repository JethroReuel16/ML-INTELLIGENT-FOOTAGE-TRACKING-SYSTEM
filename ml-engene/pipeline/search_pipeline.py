import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone

from ml_config import (
    DetectorConfig,
    dino_settings,
    high_detail_imgsz,
    parse_text_prompts,
    save_debug_crops,
)
from detection.base import DetectorCapabilityError
from utils.image_utils import crop_object
from video.processor import VideoProcessor

logger = logging.getLogger(__name__)

SEARCH_MODE_IMAGE = "image"
SEARCH_MODE_TEXT = "text"
SEARCH_MODE_IMAGE_TEXT = "image_text"
SEARCH_MODES = (SEARCH_MODE_IMAGE, SEARCH_MODE_TEXT, SEARCH_MODE_IMAGE_TEXT)

RANKING_BASIS_SIMILARITY = "dinov2_similarity"
RANKING_BASIS_CONFIDENCE = "detection_confidence"

# Ranking-score threshold for a "candidate" label. Labels are interpretation
# aids, not probabilities.
CANDIDATE_THRESHOLD = 0.10

# Objects covering most of the frame are almost always false positives.
MAX_BOX_AREA_RATIO = 0.70

EVIDENCE_JPEG_QUALITY = 92

# How often a running search logs its progress.
PROGRESS_LOG_SECONDS = 15


def resolve_search_mode(reference_image, text_prompt, requested=None):
    """Validate the inputs and return one of SEARCH_MODES."""

    has_image = bool(reference_image)
    has_text = bool(parse_text_prompts(text_prompt))

    if requested:
        requested = str(requested).strip().lower()

        if requested not in SEARCH_MODES:
            raise ValueError(
                f"search_mode must be one of: {', '.join(SEARCH_MODES)}."
            )

    if has_image and has_text:
        mode = SEARCH_MODE_IMAGE_TEXT
    elif has_image:
        mode = SEARCH_MODE_IMAGE
    elif has_text:
        mode = SEARCH_MODE_TEXT
    else:
        raise ValueError(
            "Provide a reference image, a text description, or both."
        )

    if requested and requested != mode:
        raise ValueError(
            f"search_mode '{requested}' does not match the supplied inputs "
            f"(image={'yes' if has_image else 'no'}, "
            f"text={'yes' if has_text else 'no'})."
        )

    return mode


class VisionTracePipeline:
    """
    ML Footage Tracking System - object-search pipeline.

    Workflow:
    Detector (YOLOE or legacy YOLO11n, chosen by configuration)
    -> ByteTrack tracking -> object crops -> DINOv2 embeddings (batched)
    -> cosine similarity against the reference image
    -> track aggregation -> ranked matches -> evidence images.

    Search modes:
      image       reference image only (default categories are detected,
                  candidates are ranked by DINOv2 similarity)
      image_text  text prompt selects what to detect, the image ranks it
      text        text prompt only: there is no reference embedding, so
                  candidates are ranked by detection confidence and no
                  similarity score is reported.

    Search records are persisted by the FastAPI backend in PostgreSQL.
    (Class name kept for import compatibility.)
    """

    def __init__(
        self,
        model_path=None,
        debug_folder="debug_crops",
        results_folder="results",
        allowed_classes=None,
        detector=None,
        detector_status=None,
        tracker_factory=None,
        extractor=None,
        similarity=None,
        config=None,
    ):
        started = time.monotonic()

        self.config = config or DetectorConfig.from_env()
        self.debug_folder = debug_folder
        self.results_folder = results_folder
        self.save_debug_crops = save_debug_crops()

        os.makedirs(self.results_folder, exist_ok=True)
        if self.save_debug_crops:
            os.makedirs(self.debug_folder, exist_ok=True)

        # One search at a time per pipeline: detector prompts are shared
        # model state and the models are large.
        self._lock = threading.Lock()

        if detector is None:
            from detection.factory import create_detector

            detector, detector_status = create_detector(self.config)

        self.detector = detector
        self.detector_status = detector_status or {
            "requested": detector.name,
            "active": detector.name,
            "checkpoint": detector.checkpoint,
            "device": self.config.device,
            "fallback": False,
            "fallback_reason": None,
        }

        # Legacy override kept for compatibility with older callers.
        self._legacy_allowed = (
            set(allowed_classes) if allowed_classes else None
        )

        if tracker_factory is None:
            from tracking.object_tracker import ObjectTracker

            tracker_factory = ObjectTracker

        self._tracker_factory = tracker_factory
        self.tracker = self._new_tracker(None)

        if extractor is None:
            from embedding.feature_extractor import DINOv2FeatureExtractor

            extractor = DINOv2FeatureExtractor(**dino_settings(self.config.device))

        self.extractor = extractor

        if similarity is None:
            from matching.similarity import SimilarityEngine

            similarity = SimilarityEngine()

        self.similarity = similarity

        logger.info(
            "ML engine ready in %.1fs (detector=%s, requested=%s, device=%s%s)",
            time.monotonic() - started,
            self.detector_status["active"],
            self.detector_status["requested"],
            self.detector_status.get("device"),
            ", FALLBACK" if self.detector_status.get("fallback") else "",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_tracker(self, activation_threshold):
        """Fresh tracker per video; pass the user's confidence floor when supported."""
        if activation_threshold is not None:
            try:
                return self._tracker_factory(activation_threshold=activation_threshold)
            except TypeError:
                pass  # simple factories (e.g. test fakes) take no arguments
        return self._tracker_factory()

    def create_reference_embedding(self, reference_image):
        """Create a DINOv2 embedding from the reference image."""

        if isinstance(reference_image, str) and not os.path.isfile(reference_image):
            raise FileNotFoundError(f"Reference image not found: {reference_image}")

        return self.extractor.extract(reference_image)

    def _score_crops(self, crops, reference_embedding):
        """Similarity of each crop to the reference, batched when supported."""
        batch_extract = getattr(self.extractor, "extract_batch", None)
        batch_similarity = getattr(self.similarity, "cosine_similarity_many", None)

        if batch_extract is not None and batch_similarity is not None:
            return batch_similarity(reference_embedding, batch_extract(crops))

        return [
            self.similarity.cosine_similarity(reference_embedding, self.extractor.extract(crop))
            for crop in crops
        ]

    # ------------------------------------------------------------------
    # Search entry point
    # ------------------------------------------------------------------

    def search(
        self,
        reference_image=None,
        video_path=None,
        frame_interval=5,
        min_detection_confidence=0.25,
        max_results=20,
        owner_id=None,
        text_prompt=None,
        search_mode=None,
        high_detail=False,
    ):
        """
        Run a complete search (image, text, or image + text).

        high_detail runs the detector at a larger input size so small objects
        (shoes, phones, watches) in high-resolution footage are found, at
        roughly 3x the detection cost.
        """

        if not video_path or not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if owner_id is not None:
            owner_id = str(owner_id)

        mode = resolve_search_mode(reference_image, text_prompt, search_mode)
        prompts = parse_text_prompts(text_prompt)

        if mode != SEARCH_MODE_IMAGE:
            self._require_text_prompts()

        with self._lock:
            base_imgsz = getattr(self.detector, "imgsz", None)
            if high_detail and base_imgsz is not None:
                self.detector.imgsz = max(base_imgsz, high_detail_imgsz())
            try:
                return self._search_locked(
                    mode=mode,
                    prompts=prompts,
                    reference_image=reference_image,
                    video_path=video_path,
                    frame_interval=frame_interval,
                    min_detection_confidence=min_detection_confidence,
                    max_results=max_results,
                    owner_id=owner_id,
                    text_prompt=text_prompt,
                )
            finally:
                # The detector is shared: never leak one search's size into the next.
                if base_imgsz is not None:
                    self.detector.imgsz = base_imgsz

    def _require_text_prompts(self):
        if self.detector.supports_text_prompts:
            return

        status = self.detector_status

        reason = (
            f" The requested detector '{status['requested']}' failed to "
            f"load ({status['fallback_reason']})."
            if status.get("fallback")
            else ""
        )

        raise DetectorCapabilityError(
            "Text-based search needs the YOLOE detector, but the active "
            f"detector is '{self.detector.name}'.{reason}"
        )

    def _search_locked(
        self,
        mode,
        prompts,
        reference_image,
        video_path,
        frame_interval,
        min_detection_confidence,
        max_results,
        owner_id,
        text_prompt,
    ):
        allowed_class_ids = self.detector.configure_search(
            text_prompts=prompts or None,
            reference_image=reference_image,
            confidence=min_detection_confidence,
        )

        if self._legacy_allowed is not None and allowed_class_ids is not None:
            allowed_class_ids = set(self._legacy_allowed)

        reference_embedding = None

        if mode != SEARCH_MODE_TEXT:
            reference_embedding = self.create_reference_embedding(reference_image)

        ranking_basis = (
            RANKING_BASIS_SIMILARITY
            if reference_embedding is not None
            else RANKING_BASIS_CONFIDENCE
        )

        search_result = self.search_video(
            video_path=video_path,
            reference_embedding=reference_embedding,
            frame_interval=frame_interval,
            min_detection_confidence=min_detection_confidence,
            max_results=max_results,
            allowed_class_ids=allowed_class_ids,
        )

        summary = search_result["summary"]
        candidates = search_result["results"]

        search_id = self._create_search_id()
        search_folder = os.path.join(self.results_folder, search_id)
        evidence_folder = os.path.join(search_folder, "evidence")
        os.makedirs(evidence_folder, exist_ok=True)

        matches = []

        for rank, candidate in enumerate(candidates, start=1):
            evidence_image = self._save_evidence_image(candidate, rank, evidence_folder)

            matches.append({
                "rank": rank,
                "track_id": candidate["track_id"],
                "class_id": candidate["class_id"],
                "class_name": candidate["class_name"],
                "match_status": self._get_match_status(
                    rank=rank,
                    ranking_score=candidate["combined_score"],
                ),
                "similarity_score": (
                    round(candidate["best_similarity"], 6)
                    if ranking_basis == RANKING_BASIS_SIMILARITY
                    else None
                ),
                "ranking_basis": ranking_basis,
                "search_prompt": text_prompt or None,
                "ranking_score": round(candidate["combined_score"], 6),
                "top3_average": round(candidate["top3_average"], 6),
                "average_similarity": (
                    round(candidate["average_similarity"], 6)
                    if ranking_basis == RANKING_BASIS_SIMILARITY
                    else None
                ),
                "timestamp": round(candidate["best_timestamp"], 3),
                "frame_number": candidate["best_frame"],
                "bbox": candidate["bbox"],
                "detection_confidence": round(candidate["confidence"], 6),
                "frames_observed": candidate["frame_count"],
                "evidence_image": evidence_image,
            })

        video_info = summary["video_info"]

        report = {
            "status": "completed",
            "search_id": search_id,
            "owner_id": owner_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reference": {
                "image": reference_image,
                "text_prompt": text_prompt or None,
            },
            "video": {
                "path": video_path,
                "duration": round(video_info["duration"], 3),
                "fps": round(video_info["fps"], 3),
                "frame_count": video_info["frame_count"],
                "width": video_info["width"],
                "height": video_info["height"],
            },
            "search": {
                "search_mode": mode,
                "text_prompt": text_prompt or None,
                "prompts": prompts or (
                    list(self.config.default_categories)
                    if self.detector.supports_text_prompts
                    else None
                ),
                "ranking_basis": ranking_basis,
                "detector": dict(
                    self.detector_status,
                    **{"capabilities": self.detector.info()},
                ),
                "frame_interval": frame_interval,
                "minimum_detection_confidence": min_detection_confidence,
                "detection_size": getattr(self.detector, "imgsz", None),
                "frames_analyzed": summary["frames_analyzed"],
                "candidate_observations": summary["candidate_observations"],
                "unique_tracks": summary["unique_tracks"],
                "candidates": len(matches),
                "processing_seconds": summary["processing_seconds"],
            },
            "matches": matches,
            "files": {
                "search_folder": search_folder,
                "evidence_folder": evidence_folder,
            },
        }

        logger.info(
            "Search %s: %d frame(s) analysed in %.1fs, %d track(s), %d match(es)",
            search_id,
            summary["frames_analyzed"],
            summary["processing_seconds"],
            summary["unique_tracks"],
            len(matches),
        )

        return report

    # ------------------------------------------------------------------
    # Video analysis
    # ------------------------------------------------------------------

    def search_video(
        self,
        video_path,
        reference_embedding,
        frame_interval=5,
        min_detection_confidence=0.25,
        max_results=20,
        allowed_class_ids=None,
    ):
        """
        Search one video.

        reference_embedding may be None (text-only search): candidates are
        then scored with their detection confidence instead of DINOv2
        similarity. The two are never mixed in one search.
        """

        if frame_interval < 1:
            raise ValueError("frame_interval must be at least 1.")

        if not 0 <= min_detection_confidence <= 1:
            raise ValueError("min_detection_confidence must be between 0 and 1.")

        if max_results is not None and max_results < 1:
            raise ValueError("max_results must be at least 1 or None.")

        started = time.monotonic()

        # A fresh tracker per video, able to start tracks at the user's
        # confidence floor (ByteTrack's default would silently drop
        # detections below 0.25).
        self.tracker = self._new_tracker(min_detection_confidence)

        processor = VideoProcessor(video_path)
        video_info = processor.get_video_info()

        logger.info(
            "Analysing %s (%dx%d, %.2f fps, %d frames) every %d frame(s)",
            os.path.basename(video_path),
            video_info["width"],
            video_info["height"],
            video_info["fps"],
            video_info["frame_count"],
            frame_interval,
        )

        frame_results = []
        best_crops = {}  # track_id -> (similarity, PIL crop) for evidence
        frames_analyzed = 0

        # Long videos take minutes on CPU: report progress so the log never
        # looks stalled.
        total_to_analyse = (
            -(-video_info["frame_count"] // frame_interval) if video_info["frame_count"] else 0
        )
        last_progress = started

        try:
            for frame_result in processor.process_frames(
                self.detector,
                frame_interval=frame_interval,
            ):
                frames_analyzed += 1

                now = time.monotonic()
                if now - last_progress >= PROGRESS_LOG_SECONDS:
                    last_progress = now
                    elapsed = now - started
                    if total_to_analyse:
                        done = min(frames_analyzed / total_to_analyse, 1.0)
                        remaining = elapsed / done - elapsed if done else 0
                        logger.info(
                            "Search progress: %d/%d frames (%.0f%%), %d observation(s), "
                            "elapsed %.0fs, about %.0fs remaining",
                            frames_analyzed, total_to_analyse, done * 100,
                            len(frame_results), elapsed, remaining,
                        )
                    else:
                        logger.info(
                            "Search progress: %d frame(s) analysed, elapsed %.0fs",
                            frames_analyzed, elapsed,
                        )

                frame_number = frame_result["frame_number"]
                timestamp = frame_result["timestamp"]
                frame = frame_result["frame"]

                detections = [
                    d for d in frame_result["detections"]
                    if d["confidence"] >= min_detection_confidence
                ]

                if not detections:
                    continue

                frame_height, frame_width = frame.shape[:2]
                frame_area = frame_width * frame_height

                # Collect this frame's valid objects first, then embed them
                # in a single batch.
                observations = []

                for obj in self.tracker.update(detections):
                    if (
                        allowed_class_ids is not None
                        and obj["class_id"] not in allowed_class_ids
                    ):
                        continue

                    x1, y1, x2, y2 = obj["bbox"]
                    box_width, box_height = x2 - x1, y2 - y1

                    if box_width <= 0 or box_height <= 0:
                        continue

                    area_ratio = (box_width * box_height) / frame_area if frame_area > 0 else 0

                    if area_ratio > MAX_BOX_AREA_RATIO:
                        continue

                    crop = crop_object(frame, obj["bbox"])

                    if crop is None:
                        continue

                    observations.append((obj, crop, area_ratio))

                if not observations:
                    continue

                if reference_embedding is not None:
                    scores = self._score_crops([crop for _, crop, _ in observations], reference_embedding)
                else:
                    # Text-only search: no reference to compare with.
                    scores = [float(obj["confidence"]) for obj, _, _ in observations]

                for (obj, crop, area_ratio), score in zip(observations, scores, strict=True):
                    track_id = obj["track_id"]
                    class_id = obj["class_id"]
                    score = float(score)

                    crop_path = None
                    if self.save_debug_crops:
                        crop_path = os.path.join(
                            self.debug_folder,
                            f"frame_{frame_number}_track_{track_id}_class_{class_id}.jpg",
                        )
                        crop.save(crop_path)

                    # Keep only the best-scoring crop per track (first wins on ties,
                    # matching aggregate_tracks' choice of best observation).
                    previous = best_crops.get(track_id)
                    if previous is None or score > previous[0]:
                        best_crops[track_id] = (score, crop)

                    frame_results.append({
                        "frame_number": frame_number,
                        "timestamp": timestamp,
                        "track_id": track_id,
                        "class_id": class_id,
                        "class_name": self._get_class_name(class_id),
                        "confidence": obj["confidence"],
                        "bbox": obj["bbox"],
                        "similarity": score,
                        "crop_path": crop_path,
                        "area_ratio": area_ratio,
                    })

                    logger.debug(
                        "Frame %05d | %7.2fs | track %3d | class %2d | score %.4f",
                        frame_number, timestamp, track_id, class_id, score,
                    )
        finally:
            processor.close()

        # Container metadata may be corrected after a full read.
        video_info["frame_count"] = max(video_info["frame_count"], processor.frame_count)
        if video_info["fps"] > 0:
            video_info["duration"] = video_info["frame_count"] / video_info["fps"]

        track_results = self.aggregate_tracks(frame_results)

        if max_results is not None:
            track_results = track_results[:max_results]

        for track in track_results:
            best = best_crops.get(track["track_id"])
            track["crop"] = best[1] if best else None

        summary = {
            "video": video_path,
            "video_info": video_info,
            "frames_analyzed": frames_analyzed,
            "candidate_observations": len(frame_results),
            "unique_tracks": len(self._get_unique_track_ids(frame_results)),
            "results": len(track_results),
            "processing_seconds": round(time.monotonic() - started, 2),
        }

        return {
            "summary": summary,
            "results": track_results,
        }

    def aggregate_tracks(self, results):
        """Aggregate frame-level observations into tracks."""

        tracks = {}

        for result in results:
            track = tracks.setdefault(result["track_id"], {
                "track_id": result["track_id"],
                "class_id": result["class_id"],
                "class_name": result["class_name"],
                "frames": [],
                "scores": [],
            })
            track["frames"].append(result)
            track["scores"].append(result["similarity"])

        aggregated = []

        for track in tracks.values():
            scores = track["scores"]

            if not scores:
                continue

            best_result = max(track["frames"], key=lambda item: item["similarity"])
            average_score = sum(scores) / len(scores)
            top_scores = sorted(scores, reverse=True)[:3]
            top3_average = sum(top_scores) / len(top_scores)

            combined_score = (
                0.50 * best_result["similarity"]
                + 0.30 * top3_average
                + 0.20 * average_score
            )

            aggregated.append({
                "track_id": track["track_id"],
                "class_id": track["class_id"],
                "class_name": track["class_name"],
                "best_similarity": best_result["similarity"],
                "top3_average": top3_average,
                "average_similarity": average_score,
                "combined_score": combined_score,
                "best_timestamp": best_result["timestamp"],
                "best_frame": best_result["frame_number"],
                "confidence": best_result["confidence"],
                "bbox": best_result["bbox"],
                "crop_path": best_result["crop_path"],
                "area_ratio": best_result["area_ratio"],
                "frame_count": len(track["frames"]),
                "frames": track["frames"],
            })

        aggregated.sort(key=lambda item: item["combined_score"], reverse=True)

        return aggregated

    @staticmethod
    def _get_match_status(rank, ranking_score):
        """
        Assign an interpretation label, not a probability.

        The top-ranked track is only called a "top candidate" when it also
        clears the candidate threshold; a weak best match is still weak.
        """
        if ranking_score < CANDIDATE_THRESHOLD:
            return "LOW SIMILARITY"

        if rank == 1:
            return "TOP CANDIDATE"

        return "CANDIDATE"

    def _save_evidence_image(self, candidate, rank, evidence_folder):
        """Write the best crop of a candidate track as permanent evidence."""

        destination = os.path.join(
            evidence_folder,
            f"rank_{rank:02d}_track_{candidate['track_id']}.jpg",
        )

        crop = candidate.get("crop")

        if crop is not None:
            crop.save(destination, format="JPEG", quality=EVIDENCE_JPEG_QUALITY)
        elif candidate.get("crop_path") and os.path.isfile(candidate["crop_path"]):
            import shutil

            shutil.copy2(candidate["crop_path"], destination)

        return destination

    @staticmethod
    def _create_search_id():
        """Unique, sortable search ID (safe across several backend processes)."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        return f"search_{timestamp}_{uuid.uuid4().hex[:6]}"

    def _get_class_name(self, class_id):
        return self.detector.class_name(class_id)

    @staticmethod
    def _get_unique_track_ids(results):
        return {result["track_id"] for result in results}
