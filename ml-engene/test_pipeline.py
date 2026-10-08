
from pprint import pprint

from pipeline.search_pipeline import VisionTracePipeline


REFERENCE_IMAGE = "embedding/reference.jpg"
VIDEO_PATH = "test_video.mp4"


def main():
    print("=" * 60)
    print("VISIONTRACE AI - FINAL ML PIPELINE TEST")
    print("=" * 60)

    pipeline = VisionTracePipeline()

    report = pipeline.search(
        reference_image=REFERENCE_IMAGE,
        video_path=VIDEO_PATH,
        frame_interval=5,
        min_detection_confidence=0.25,
        max_results=20,
    )

    print("\n" + "=" * 60)
    print("FINAL SEARCH REPORT")
    print("=" * 60)

    print(f"Status: {report['status']}")
    print(f"Video: {report['video']['path']}")
    print(f"Duration: {report['video']['duration']:.2f}s")
    print(f"FPS: {report['video']['fps']:.2f}")
    print(f"Frames in video: {report['video']['frame_count']}")

    print("\nSEARCH STATISTICS")
    print("-" * 40)

    for key, value in report["search"].items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    if not report["matches"]:
        print("\nNo candidate matches were found.")
        return

    print("\nRANKED CANDIDATE MATCHES")
    print("-" * 60)

    for match in report["matches"]:
        print(f"\nCandidate #{match['rank']}")
        print("-" * 40)
        print(f"Object: {match['class_name']}")
        print(f"Track ID: {match['track_id']}")
        print(f"Similarity Score: {match['similarity_score']:.4f}")
        print(f"Ranking Score: {match['ranking_score']:.4f}")
        print(f"Timestamp: {match['timestamp']:.2f}s")
        print(f"Frame: {match['frame_number']}")
        print(f"Frames Observed: {match['frames_observed']}")
        print(
            "Detection Confidence: "
            f"{match['detection_confidence']:.4f}"
        )
        print(f"Bounding Box: {match['bbox']}")
        print(f"Evidence Image: {match['evidence_image']}")

    print("\nSearch finished successfully.")
    print("Review the evidence images to assess candidate matches.")


if __name__ == "__main__":
    main()