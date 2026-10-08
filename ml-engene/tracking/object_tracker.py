import numpy as np
import supervision as sv


class ObjectTracker:
    def __init__(self):
        print("Loading ByteTrack tracker...")

        self.tracker = sv.ByteTrack()

        print("ByteTrack tracker loaded.")

    def update(self, detections):

        if not detections:
            return []

        xyxy = np.array(
            [detection["bbox"] for detection in detections],
            dtype=np.float32
        )

        confidence = np.array(
            [detection["confidence"] for detection in detections],
            dtype=np.float32
        )

        class_id = np.array(
            [detection["class_id"] for detection in detections],
            dtype=int
        )

        sv_detections = sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
        )

        tracked = self.tracker.update_with_detections(
            sv_detections
        )

        results = []

        if tracked.tracker_id is None:
            return results

        for i in range(len(tracked.xyxy)):

            results.append(
                {
                    "track_id": int(tracked.tracker_id[i]),

                    "class_id": int(tracked.class_id[i]),

                    "confidence": float(
                        tracked.confidence[i]
                    ),

                    "bbox": [
                        int(value)
                        for value in tracked.xyxy[i]
                    ],
                }
            )

        return results