import json
import os
import shutil
from datetime import datetime

from detection.yolo_detector import YOLODetector
from tracking.object_tracker import ObjectTracker
from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine
from video.processor import VideoProcessor
from utils.image_utils import crop_object


class VisionTracePipeline:
    """
    VisionTrace AI object-search pipeline.

    Workflow:

    Reference image
        ↓
    DINOv2 embedding
        ↓
    Video
        ↓
    YOLO detection
        ↓
    ByteTrack tracking
        ↓
    Object crops
        ↓
    DINOv2 embeddings
        ↓
    Cosine similarity
        ↓
    Track aggregation
        ↓
    Ranked candidate matches
        ↓
    Match status
        ↓
    Evidence + JSON result
    """

    def __init__(
        self,
        model_path="yolo11n.pt",
        debug_folder="debug_crops",
        results_folder="results",
        allowed_classes=(24, 26, 28),
    ):
        print("=" * 60)
        print("VISIONTRACE AI - ML ENGINE")
        print("=" * 60)

        self.debug_folder = debug_folder
        self.results_folder = results_folder
        self.allowed_classes = set(allowed_classes)

        os.makedirs(self.debug_folder, exist_ok=True)
        os.makedirs(self.results_folder, exist_ok=True)

        print("\nLoading YOLO...")
        self.detector = YOLODetector(model_path=model_path)

        print("\nLoading ByteTrack...")
        self.tracker = ObjectTracker()

        print("\nLoading DINOv2...")
        self.extractor = DINOv2FeatureExtractor()

        print("\nLoading similarity engine...")
        self.similarity = SimilarityEngine()

        print("\n" + "=" * 60)
        print("VISIONTRACE ML ENGINE READY")
        print("=" * 60)

    def create_reference_embedding(self, reference_image):
        """Create a DINOv2 embedding from the reference image."""

        if isinstance(reference_image, str):
            if not os.path.isfile(reference_image):
                raise FileNotFoundError(
                    f"Reference image not found: {reference_image}"
                )

        print("\nCreating reference embedding...")

        embedding = self.extractor.extract(reference_image)

        print("Reference embedding created.")

        return embedding

    def search(
        self,
        reference_image,
        video_path,
        frame_interval=5,
        min_detection_confidence=0.25,
        max_results=20,
    ):
        """
        Run a complete VisionTrace search.

        This method:
        1. Creates the reference embedding.
        2. Searches the video.
        3. Ranks candidates.
        4. Assigns match-status labels.
        5. Saves evidence images.
        6. Saves JSON search results.
        """

        if not os.path.isfile(video_path):
            raise FileNotFoundError(
                f"Video file not found: {video_path}"
            )

        reference_embedding = self.create_reference_embedding(
            reference_image
        )

        search_result = self.search_video(
            video_path=video_path,
            reference_embedding=reference_embedding,
            frame_interval=frame_interval,
            min_detection_confidence=min_detection_confidence,
            max_results=max_results,
        )

        summary = search_result["summary"]
        candidates = search_result["results"]

        # Create a unique directory for this search.
        search_id = self._create_search_id()

        search_folder = os.path.join(
            self.results_folder,
            search_id,
        )

        evidence_folder = os.path.join(
            search_folder,
            "evidence",
        )

        os.makedirs(evidence_folder, exist_ok=True)

        matches = []

        for rank, candidate in enumerate(candidates, start=1):

            evidence_image = self._save_evidence_image(
                candidate,
                rank,
                evidence_folder,
            )

            match_status = self._get_match_status(
                rank=rank,
                ranking_score=candidate["combined_score"],
            )

            matches.append({
                "rank": rank,
                "track_id": candidate["track_id"],
                "class_id": candidate["class_id"],
                "class_name": candidate["class_name"],
                "match_status": match_status,
                "similarity_score": round(
                    candidate["best_similarity"],
                    6,
                ),
                "ranking_score": round(
                    candidate["combined_score"],
                    6,
                ),
                "top3_average": round(
                    candidate["top3_average"],
                    6,
                ),
                "average_similarity": round(
                    candidate["average_similarity"],
                    6,
                ),
                "timestamp": round(
                    candidate["best_timestamp"],
                    3,
                ),
                "frame_number": candidate["best_frame"],
                "bbox": candidate["bbox"],
                "detection_confidence": round(
                    candidate["confidence"],
                    6,
                ),
                "frames_observed": candidate["frame_count"],
                "evidence_image": evidence_image,
            })

        report = {
            "status": "completed",
            "search_id": search_id,
            "created_at": datetime.now().isoformat(),

            "reference": {
                "image": reference_image,
            },

            "video": {
                "path": video_path,
                "duration": round(
                    summary["video_info"]["duration"],
                    3,
                ),
                "fps": round(
                    summary["video_info"]["fps"],
                    3,
                ),
                "frame_count": summary["video_info"]["frame_count"],
                "width": summary["video_info"]["width"],
                "height": summary["video_info"]["height"],
            },

            "search": {
                "frame_interval": frame_interval,
                "minimum_detection_confidence": (
                    min_detection_confidence
                ),
                "frames_analyzed": summary["frames_analyzed"],
                "candidate_observations": (
                    summary["candidate_observations"]
                ),
                "unique_tracks": summary["unique_tracks"],
                "candidates": len(matches),
            },

            "matches": matches,
        }

        result_path = os.path.join(
            search_folder,
            "result.json",
        )

        summary_path = os.path.join(
            search_folder,
            "summary.json",
        )

        self._save_json(report, result_path)

        summary_report = {
            "status": report["status"],
            "search_id": report["search_id"],
            "created_at": report["created_at"],
            "video": report["video"],
            "search": report["search"],
            "top_match": (
                matches[0]
                if matches
                else None
            ),
        }

        self._save_json(
            summary_report,
            summary_path,
        )

        report["files"] = {
            "search_folder": search_folder,
            "result_json": result_path,
            "summary_json": summary_path,
            "evidence_folder": evidence_folder,
        }

        print("\n" + "=" * 60)
        print("RESULTS SAVED")
        print("=" * 60)

        print(f"Search ID: {search_id}")
        print(f"Result: {result_path}")
        print(f"Summary: {summary_path}")
        print(f"Evidence: {evidence_folder}")

        return report

    def search_video(
        self,
        video_path,
        reference_embedding,
        frame_interval=5,
        min_detection_confidence=0.25,
        max_results=20,
    ):
        """Search one video using an existing reference embedding."""

        if frame_interval < 1:
            raise ValueError(
                "frame_interval must be at least 1."
            )

        if not 0 <= min_detection_confidence <= 1:
            raise ValueError(
                "min_detection_confidence must be "
                "between 0 and 1."
            )

        if max_results is not None and max_results < 1:
            raise ValueError(
                "max_results must be at least 1 or None."
            )

        print("\n" + "=" * 60)
        print("VISIONTRACE VIDEO SEARCH")
        print("=" * 60)

        print(f"Video: {video_path}")
        print(f"Frame interval: {frame_interval}")

        print(
            "Minimum detection confidence: "
            f"{min_detection_confidence}"
        )

        # New tracker for every video.
        self.tracker = ObjectTracker()

        processor = VideoProcessor(video_path)
        video_info = processor.get_video_info()

        print("\nVIDEO INFORMATION")
        print("-" * 60)

        print(
            f"Resolution: "
            f"{video_info['width']}x"
            f"{video_info['height']}"
        )

        print(f"FPS: {video_info['fps']:.2f}")
        print(f"Frames: {video_info['frame_count']}")

        print(
            f"Duration: "
            f"{video_info['duration']:.2f}s"
        )

        frame_results = []
        frames_analyzed = 0

        try:
            for frame_result in processor.process_frames(
                self.detector,
                frame_interval=frame_interval,
            ):

                frames_analyzed += 1

                frame_number = frame_result["frame_number"]
                timestamp = frame_result["timestamp"]
                frame = frame_result["frame"]

                detections = frame_result["detections"]

                detections = [
                    detection
                    for detection in detections
                    if detection["confidence"]
                    >= min_detection_confidence
                ]

                if not detections:
                    continue

                tracked_objects = self.tracker.update(
                    detections
                )

                for obj in tracked_objects:

                    if obj["class_id"] not in self.allowed_classes:
                        continue

                    track_id = obj["track_id"]
                    class_id = obj["class_id"]
                    bbox = obj["bbox"]
                    confidence = obj["confidence"]

                    x1, y1, x2, y2 = bbox

                    frame_height, frame_width = (
                        frame.shape[:2]
                    )

                    box_width = x2 - x1
                    box_height = y2 - y1

                    if box_width <= 0 or box_height <= 0:
                        continue

                    box_area = box_width * box_height
                    frame_area = frame_width * frame_height

                    area_ratio = (
                        box_area / frame_area
                        if frame_area > 0
                        else 0
                    )

                    # Ignore detections occupying most
                    # of the frame.
                    if area_ratio > 0.70:
                        continue

                    object_crop = crop_object(
                        frame,
                        bbox,
                    )

                    if object_crop is None:
                        continue

                    crop_filename = (
                        f"frame_{frame_number}"
                        f"_track_{track_id}"
                        f"_class_{class_id}.jpg"
                    )

                    crop_path = os.path.join(
                        self.debug_folder,
                        crop_filename,
                    )

                    object_crop.save(crop_path)

                    object_embedding = (
                        self.extractor.extract(
                            object_crop
                        )
                    )

                    similarity_score = (
                        self.similarity.cosine_similarity(
                            reference_embedding,
                            object_embedding,
                        )
                    )

                    class_name = self._get_class_name(
                        class_id
                    )

                    result = {
                        "frame_number": frame_number,
                        "timestamp": timestamp,
                        "track_id": track_id,
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox": bbox,
                        "similarity": similarity_score,
                        "crop_path": crop_path,
                        "area_ratio": area_ratio,
                    }

                    frame_results.append(result)

                    print(
                        f"Frame {frame_number:04d} | "
                        f"{timestamp:7.2f}s | "
                        f"Track {track_id:3d} | "
                        f"Class {class_id:2d} | "
                        f"Similarity "
                        f"{similarity_score:.4f}"
                    )

        finally:
            processor.close()

        track_results = self.aggregate_tracks(
            frame_results
        )

        if max_results is not None:
            track_results = track_results[:max_results]

        unique_tracks = self._get_unique_track_ids(
            frame_results
        )

        summary = {
            "video": video_path,
            "video_info": video_info,
            "frames_analyzed": frames_analyzed,
            "candidate_observations": len(
                frame_results
            ),
            "unique_tracks": len(unique_tracks),
            "results": len(track_results),
        }

        print("\n" + "=" * 60)
        print("SEARCH COMPLETE")
        print("=" * 60)

        print(
            f"Frames analyzed: "
            f"{frames_analyzed}"
        )

        print(
            "Candidate observations: "
            f"{len(frame_results)}"
        )

        print(
            f"Unique tracks: "
            f"{len(unique_tracks)}"
        )

        print(
            f"Ranked candidates: "
            f"{len(track_results)}"
        )

        print("\nTOP CANDIDATES")
        print("-" * 60)

        for index, result in enumerate(
            track_results,
            start=1,
        ):

            match_status = self._get_match_status(
                rank=index,
                ranking_score=result["combined_score"],
            )

            print(
                f"{index}. "
                f"{match_status} | "
                f"Track {result['track_id']} | "
                f"{result['class_name']} | "
                f"Ranking Score "
                f"{result['combined_score']:.4f} | "
                f"Best Similarity "
                f"{result['best_similarity']:.4f} | "
                f"Time "
                f"{result['best_timestamp']:.2f}s"
            )

        return {
            "summary": summary,
            "results": track_results,
        }

    def aggregate_tracks(self, results):
        """Aggregate frame-level observations into tracks."""

        tracks = {}

        for result in results:

            track_id = result["track_id"]

            if track_id not in tracks:
                tracks[track_id] = {
                    "track_id": track_id,
                    "class_id": result["class_id"],
                    "class_name": result["class_name"],
                    "frames": [],
                    "scores": [],
                }

            tracks[track_id]["frames"].append(
                result
            )

            tracks[track_id]["scores"].append(
                result["similarity"]
            )

        aggregated = []

        for track in tracks.values():

            scores = track["scores"]

            if not scores:
                continue

            best_result = max(
                track["frames"],
                key=lambda item: item["similarity"],
            )

            average_score = (
                sum(scores) / len(scores)
            )

            top_scores = sorted(
                scores,
                reverse=True,
            )[:3]

            top3_average = (
                sum(top_scores) / len(top_scores)
            )

            # Experimental ranking score.
            # This is NOT a probability.
            combined_score = (
                0.50 * best_result["similarity"]
                + 0.30 * top3_average
                + 0.20 * average_score
            )

            aggregated.append({
                "track_id": track["track_id"],
                "class_id": track["class_id"],
                "class_name": track["class_name"],
                "best_similarity": (
                    best_result["similarity"]
                ),
                "top3_average": top3_average,
                "average_similarity": average_score,
                "combined_score": combined_score,
                "best_timestamp": (
                    best_result["timestamp"]
                ),
                "best_frame": (
                    best_result["frame_number"]
                ),
                "confidence": (
                    best_result["confidence"]
                ),
                "bbox": best_result["bbox"],
                "crop_path": (
                    best_result["crop_path"]
                ),
                "area_ratio": (
                    best_result["area_ratio"]
                ),
                "frame_count": len(
                    track["frames"]
                ),
                "frames": track["frames"],
            })

        # Ranking order is based on the same score
        # returned to the caller.
        aggregated.sort(
            key=lambda item: item["combined_score"],
            reverse=True,
        )

        return aggregated

    @staticmethod
    def _get_match_status(rank, ranking_score):
        """
        Assign a simple heuristic status to a candidate.

        IMPORTANT:
        These labels are for result interpretation only.
        They are NOT calibrated confidence probabilities.

        TOP CANDIDATE:
            The highest-ranked candidate.

        CANDIDATE:
            A candidate whose ranking score reaches the
            configured interpretation threshold.

        LOW SIMILARITY:
            A candidate below that threshold.
        """

        if rank == 1:
            return "TOP CANDIDATE"

        if ranking_score >= 0.10:
            return "CANDIDATE"

        return "LOW SIMILARITY"

    def _save_evidence_image(
        self,
        candidate,
        rank,
        evidence_folder,
    ):
        """
        Copy the best candidate crop into the
        permanent search evidence folder.
        """

        source = candidate["crop_path"]

        filename = (
            f"rank_{rank:02d}_"
            f"track_{candidate['track_id']}.jpg"
        )

        destination = os.path.join(
            evidence_folder,
            filename,
        )

        if os.path.isfile(source):
            shutil.copy2(
                source,
                destination,
            )

        return destination

    @staticmethod
    def _save_json(data, path):
        """Save a Python dictionary as formatted JSON."""

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )

    def _create_search_id(self):
        """Create a unique ID for each search."""

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        return f"search_{timestamp}"

    def _get_class_name(self, class_id):
        """Resolve YOLO class ID to class name."""

        names = self.detector.model.names

        if isinstance(names, dict):
            return names.get(
                class_id,
                f"class_{class_id}",
            )

        if 0 <= class_id < len(names):
            return names[class_id]

        return f"class_{class_id}"

    @staticmethod
    def _get_unique_track_ids(results):
        return {
            result["track_id"]
            for result in results
        }