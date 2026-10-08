from detection.yolo_detector import YOLODetector
from tracking.object_tracker import ObjectTracker
from video.processor import VideoProcessor
from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine
from utils.image_utils import crop_object


VIDEO_PATH = "test_video.mp4"


def main():

    print("=" * 60)
    print("VISIONTRACE - EMBEDDING CHANGE TEST")
    print("=" * 60)

    detector = YOLODetector()
    tracker = ObjectTracker()
    extractor = DINOv2FeatureExtractor()
    similarity = SimilarityEngine()

    processor = VideoProcessor(VIDEO_PATH)

    previous_embedding = None
    previous_track = None

    for frame_result in processor.process_frames(
        detector,
        frame_interval=5
    ):

        frame = frame_result["frame"]
        frame_number = frame_result["frame_number"]

        detections = frame_result["detections"]

        tracked_objects = tracker.update(
            detections
        )

        for obj in tracked_objects:

            if obj["track_id"] != 20:
                continue

            crop = crop_object(
                frame,
                obj["bbox"]
            )

            if crop is None:
                continue

            embedding = extractor.extract(
                crop
            )

            print(
                f"\nFrame: {frame_number}"
            )

            print(
                f"Track: {obj['track_id']}"
            )

            print(
                f"BBox: {obj['bbox']}"
            )

            print(
                f"Embedding first values: "
                f"{embedding[:5]}"
            )

            if previous_embedding is not None:

                change = similarity.cosine_similarity(
                    previous_embedding,
                    embedding
                )

                print(
                    f"Similarity with previous "
                    f"embedding: {change:.6f}"
                )

            previous_embedding = embedding
            previous_track = obj["track_id"]

    processor.close()


if __name__ == "__main__":
    main()