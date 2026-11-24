import cv2

from detection.yolo_detector import YOLODetector
from tracking.object_tracker import ObjectTracker
from video.processor import VideoProcessor


VIDEO_PATH = "test_video.mp4"
OUTPUT_PATH = "debug_detection.jpg"


def main():

    print("=" * 60)
    print("ML FOOTAGE TRACKING SYSTEM - DETECTION DEBUG")
    print("=" * 60)

    detector = YOLODetector()
    tracker = ObjectTracker()
    processor = VideoProcessor(VIDEO_PATH)

    saved = False

    for frame_result in processor.process_frames(
        detector,
        frame_interval=5
    ):

        frame = frame_result["frame"].copy()

        detections = frame_result["detections"]

        tracked_objects = tracker.update(
            detections
        )

        for obj in tracked_objects:

            x1, y1, x2, y2 = obj["bbox"]

            track_id = obj["track_id"]
            class_id = obj["class_id"]
            confidence = obj["confidence"]

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                3
            )

            label = (
                f"Track {track_id} | "
                f"Class {class_id} | "
                f"{confidence:.2f}"
            )

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 30)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        # Save the first frame containing detections
        if tracked_objects and not saved:

            cv2.imwrite(
                OUTPUT_PATH,
                frame
            )

            print(
                f"\nSaved debug frame to:"
                f"\n{OUTPUT_PATH}"
            )

            saved = True

            break

    processor.close()


if __name__ == "__main__":
    main()