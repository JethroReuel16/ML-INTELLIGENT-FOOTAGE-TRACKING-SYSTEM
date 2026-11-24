import logging
import warnings

import numpy as np
import supervision as sv

logger = logging.getLogger(__name__)

# ByteTrack's own default; detections below the activation threshold can
# never start a track.
DEFAULT_ACTIVATION_THRESHOLD = 0.25


class ObjectTracker:
    """ByteTrack wrapper (supervision). One instance per video."""

    def __init__(self, activation_threshold=DEFAULT_ACTIVATION_THRESHOLD):
        with warnings.catch_warnings():
            # sv.ByteTrack is deprecated upstream (removed in supervision 0.31);
            # requirements pin supervision<0.31 until the tracker is migrated.
            warnings.simplefilter("ignore", category=FutureWarning)
            self.tracker = sv.ByteTrack(
                track_activation_threshold=float(activation_threshold),
            )

    def update(self, detections):
        if not detections:
            return []

        sv_detections = sv.Detections(
            xyxy=np.array([d["bbox"] for d in detections], dtype=np.float32),
            confidence=np.array([d["confidence"] for d in detections], dtype=np.float32),
            class_id=np.array([d["class_id"] for d in detections], dtype=int),
        )

        tracked = self.tracker.update_with_detections(sv_detections)

        if tracked.tracker_id is None:
            return []

        return [
            {
                "track_id": int(tracked.tracker_id[i]),
                "class_id": int(tracked.class_id[i]),
                "confidence": float(tracked.confidence[i]),
                "bbox": [int(v) for v in tracked.xyxy[i]],
            }
            for i in range(len(tracked.xyxy))
        ]
