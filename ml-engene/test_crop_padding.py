import os
import cv2
from PIL import Image

from detection.yolo_detector import YOLODetector
from tracking.object_tracker import ObjectTracker
from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


VIDEO_PATH = "test_video.mp4"
REFERENCE_IMAGE = "embedding/reference.jpg"

TARGET_TRACK_ID = 26
TARGET_CLASS_ID = 26

TARGET_FRAMES = {
    320,
    325,
    330,
    335,
    340,
    345,
}

PADDING_LEVELS = [
    0.00,
    0.10,
    0.20,
    0.30,
]

OUTPUT_FOLDER = "padding_test_crops"


def crop_with_padding(frame, bbox, padding_ratio):
    """
    Crop an object bounding box with configurable padding.

    0.00 = no padding
    0.10 = 10% padding
    0.20 = 20% padding
    0.30 = 30% padding
    """

    x1, y1, x2, y2 = bbox

    frame_height, frame_width = frame.shape[:2]

    box_width = x2 - x1
    box_height = y2 - y1

    padding_x = int(box_width * padding_ratio)
    padding_y = int(box_height * padding_ratio)

    new_x1 = max(
        0,
        x1 - padding_x
    )

    new_y1 = max(
        0,
        y1 - padding_y
    )

    new_x2 = min(
        frame_width,
        x2 + padding_x
    )

    new_y2 = min(
        frame_height,
        y2 + padding_y
    )

    if new_x2 <= new_x1 or new_y2 <= new_y1:
        return None

    crop = frame[
        new_y1:new_y2,
        new_x1:new_x2
    ]

    if crop.size == 0:
        return None

    return crop


def main():

    print("=" * 75)
    print("VISIONTRACE AI - CROP PADDING EXPERIMENT")
    print("=" * 75)

    # =========================================================
    # LOAD MODELS
    # =========================================================

    print("\nLoading YOLO...")
    detector = YOLODetector()

    print("\nLoading ByteTrack...")
    tracker = ObjectTracker()

    print("\nLoading DINOv2...")
    extractor = DINOv2FeatureExtractor()

    print("\nLoading similarity engine...")
    similarity = SimilarityEngine()

    # =========================================================
    # REFERENCE EMBEDDING
    # =========================================================

    print("\n" + "=" * 75)
    print("REFERENCE IMAGE")
    print("=" * 75)

    reference_embedding = extractor.extract(
        REFERENCE_IMAGE
    )

    print(
        f"Reference embedding created: "
        f"{REFERENCE_IMAGE}"
    )

    # =========================================================
    # OUTPUT DIRECTORY
    # =========================================================

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    # =========================================================
    # OPEN VIDEO
    # =========================================================

    print("\n" + "=" * 75)
    print("PROCESSING VIDEO")
    print("=" * 75)

    capture = cv2.VideoCapture(
        VIDEO_PATH
    )

    if not capture.isOpened():
        raise ValueError(
            f"Unable to open video: {VIDEO_PATH}"
        )

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    frame_number = 0

    results = []

    # =========================================================
    # PROCESS VIDEO IN SEQUENCE
    #
    # IMPORTANT:
    # ByteTrack must see frames in sequence so that
    # Track 26 can be established correctly.
    # =========================================================

    while True:

        success, frame = capture.read()

        if not success:
            break

        # -----------------------------------------------------
        # Match the production pipeline:
        # process every 5th frame.
        # -----------------------------------------------------

        if frame_number % 5 == 0:

            detections = detector.detect(
                frame
            )

            tracked_objects = tracker.update(
                detections
            )

            # -------------------------------------------------
            # Only perform the expensive padding experiment
            # on the target frames.
            # -------------------------------------------------

            if frame_number in TARGET_FRAMES:

                for obj in tracked_objects:

                    track_id = obj["track_id"]
                    class_id = obj["class_id"]

                    if track_id != TARGET_TRACK_ID:
                        continue

                    if class_id != TARGET_CLASS_ID:
                        continue

                    bbox = obj["bbox"]

                    timestamp = (
                        frame_number / fps
                        if fps > 0
                        else 0
                    )

                    print("\n" + "-" * 75)

                    print(
                        f"Track {track_id} found"
                    )

                    print(
                        f"Frame: {frame_number}"
                    )

                    print(
                        f"Time: {timestamp:.2f}s"
                    )

                    print(
                        f"Class: {class_id}"
                    )

                    print(
                        f"Bounding box: {bbox}"
                    )

                    # =============================================
                    # TEST EACH PADDING LEVEL
                    # =============================================

                    for padding in PADDING_LEVELS:

                        crop = crop_with_padding(
                            frame,
                            bbox,
                            padding
                        )

                        if crop is None:
                            print(
                                f"Padding {int(padding * 100)}% "
                                f"-> Invalid crop"
                            )
                            continue

                        padding_percent = int(
                            padding * 100
                        )

                        crop_filename = (
                            f"frame_{frame_number}"
                            f"_track_{track_id}"
                            f"_padding_{padding_percent}.jpg"
                        )

                        crop_path = os.path.join(
                            OUTPUT_FOLDER,
                            crop_filename
                        )

                        cv2.imwrite(
                            crop_path,
                            crop
                        )

                        # =========================================
                        # CONVERT TO PIL
                        # =========================================

                        crop_rgb = cv2.cvtColor(
                            crop,
                            cv2.COLOR_BGR2RGB
                        )

                        crop_image = Image.fromarray(
                            crop_rgb
                        )

                        # =========================================
                        # CREATE DINO EMBEDDING
                        # =========================================

                        crop_embedding = (
                            extractor.extract(
                                crop_image
                            )
                        )

                        # =========================================
                        # CALCULATE SIMILARITY
                        # =========================================

                        score = (
                            similarity.cosine_similarity(
                                reference_embedding,
                                crop_embedding
                            )
                        )

                        results.append({
                            "frame": frame_number,
                            "padding": padding_percent,
                            "score": score,
                            "path": crop_path,
                        })

                        print(
                            f"Padding "
                            f"{padding_percent:>2}% "
                            f"-> Similarity: "
                            f"{score:.6f}"
                        )

        frame_number += 1

    capture.release()

    # =========================================================
    # RESULTS
    # =========================================================

    print("\n" + "=" * 75)
    print("PADDING RESULTS")
    print("=" * 75)

    if not results:

        print(
            "\nNo Track 26 detections were found."
        )

        print(
            "\nThis means Track 26 was not reproduced "
            "during this run."
        )

        print(
            "The tracker may have assigned a different "
            "ID during this run."
        )

        return

    # =========================================================
    # GROUP RESULTS BY PADDING
    # =========================================================

    padding_groups = {}

    for result in results:

        padding = result["padding"]

        if padding not in padding_groups:
            padding_groups[padding] = []

        padding_groups[padding].append(
            result["score"]
        )

    print()

    print(
        f"{'Padding':<12}"
        f"{'Average':<15}"
        f"{'Best':<15}"
        f"{'Worst':<15}"
    )

    print("-" * 57)

    summary = []

    for padding in sorted(
        padding_groups.keys()
    ):

        scores = padding_groups[padding]

        average_score = (
            sum(scores) / len(scores)
        )

        best_score = max(scores)
        worst_score = min(scores)

        summary.append({
            "padding": padding,
            "average": average_score,
            "best": best_score,
            "worst": worst_score,
        })

        print(
            f"{padding:>3}%"
            f"{'':<9}"
            f"{average_score:<15.6f}"
            f"{best_score:<15.6f}"
            f"{worst_score:<15.6f}"
        )

    # =========================================================
    # BEST PADDING BY AVERAGE
    # =========================================================

    best_padding = max(
        summary,
        key=lambda x: x["average"]
    )

    # =========================================================
    # BEST INDIVIDUAL RESULT
    # =========================================================

    best_single = max(
        results,
        key=lambda x: x["score"]
    )

    # =========================================================
    # FINAL SUMMARY
    # =========================================================

    print("\n" + "=" * 75)
    print("BEST PADDING CONFIGURATION")
    print("=" * 75)

    print(
        f"\nBest average padding: "
        f"{best_padding['padding']}%"
    )

    print(
        f"Average similarity: "
        f"{best_padding['average']:.6f}"
    )

    print(
        f"Best similarity: "
        f"{best_padding['best']:.6f}"
    )

    print(
        f"Worst similarity: "
        f"{best_padding['worst']:.6f}"
    )

    print("\nBest individual crop:")

    print(
        f"Frame: "
        f"{best_single['frame']}"
    )

    print(
        f"Padding: "
        f"{best_single['padding']}%"
    )

    print(
        f"Similarity: "
        f"{best_single['score']:.6f}"
    )

    print(
        f"Crop: "
        f"{best_single['path']}"
    )

    # =========================================================
    # IMPROVEMENT OVER 0% PADDING
    # =========================================================

    zero_padding = None

    for item in summary:

        if item["padding"] == 0:
            zero_padding = item
            break

    if zero_padding is not None:

        improvement = (
            best_padding["average"]
            - zero_padding["average"]
        )

        print("\n" + "-" * 75)

        print(
            f"Change from 0% padding: "
            f"{improvement:+.6f}"
        )

        if improvement > 0:

            print(
                "Padding improved the average "
                "reference similarity."
            )

        elif improvement < 0:

            print(
                "Padding reduced the average "
                "reference similarity."
            )

        else:

            print(
                "Padding produced the same average "
                "similarity as the original crop."
            )

    print("\n" + "=" * 75)
    print("EXPERIMENT COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()