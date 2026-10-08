from pipeline.search_pipeline import VisionTracePipeline


# ============================================================
# VISIONTRACE AI
# FINAL ML ENGINE ENTRY POINT
# ============================================================

REFERENCE_IMAGE = "reference.jpg"
VIDEO_PATH = "test_video.mp4"


def main():
    print("=" * 60)
    print("VISIONTRACE AI - ML ENGINE")
    print("=" * 60)

    print("\nInitializing VisionTrace ML pipeline...")

    # --------------------------------------------------------
    # Initialize the complete ML pipeline
    #
    # Components:
    #   YOLO      -> object detection
    #   ByteTrack -> object tracking
    #   DINOv2   -> visual feature extraction
    #   Cosine    -> visual similarity
    # --------------------------------------------------------

    pipeline = VisionTracePipeline()

    print("\nML pipeline initialized successfully.")

    print("\n" + "-" * 60)
    print("SEARCH CONFIGURATION")
    print("-" * 60)

    print(f"Reference image : {REFERENCE_IMAGE}")
    print(f"Video           : {VIDEO_PATH}")
    print("Frame interval  : 5")
    print("Min confidence  : 0.25")
    print("Maximum results : 20")

    print("\n" + "-" * 60)
    print("STARTING OBJECT SEARCH")
    print("-" * 60)

    # --------------------------------------------------------
    # Run complete object search
    # --------------------------------------------------------

    try:
        report = pipeline.search(
            reference_image=REFERENCE_IMAGE,
            video_path=VIDEO_PATH,
            frame_interval=5,
            min_detection_confidence=0.25,
            max_results=20,
        )

    except Exception as error:

        print("\n" + "=" * 60)
        print("ML ENGINE ERROR")
        print("=" * 60)

        print(f"\n{error}")

        raise

    # --------------------------------------------------------
    # Extract report information
    # --------------------------------------------------------

    search_info = report.get("search", {})
    video_info = report.get("video", {})
    matches = report.get("matches", [])
    files = report.get("files", {})

    # --------------------------------------------------------
    # Final search summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("VISIONTRACE AI - SEARCH COMPLETE")
    print("=" * 60)

    print("\nVIDEO")
    print("-" * 60)

    print(
        f"Resolution      : "
        f"{video_info.get('width')}x"
        f"{video_info.get('height')}"
    )

    print(
        f"FPS             : "
        f"{video_info.get('fps', 0):.2f}"
    )

    print(
        f"Frames          : "
        f"{video_info.get('frame_count', 0)}"
    )

    print(
        f"Duration        : "
        f"{video_info.get('duration', 0):.2f} seconds"
    )

    print("\nSEARCH")
    print("-" * 60)

    print(
        f"Frames analyzed         : "
        f"{search_info.get('frames_analyzed', 0)}"
    )

    print(
        f"Candidate observations  : "
        f"{search_info.get('candidate_observations', 0)}"
    )

    print(
        f"Unique tracks           : "
        f"{search_info.get('unique_tracks', 0)}"
    )

    print(
        f"Ranked matches          : "
        f"{len(matches)}"
    )

    # --------------------------------------------------------
    # Display top candidates
    # --------------------------------------------------------

    print("\nTOP CANDIDATES")
    print("-" * 60)

    if not matches:

        print("No candidate objects were found.")

    else:

        for index, match in enumerate(matches[:10], start=1):

            status = match.get(
                "match_status",
                "CANDIDATE"
            )

            track_id = match.get(
                "track_id",
                "N/A"
            )

            class_name = match.get(
                "class_name",
                "unknown"
            )

            ranking_score = match.get(
                "ranking_score",
                0.0
            )

            # The pipeline uses best_similarity.
            best_similarity = match.get(
                "best_similarity",
                0.0
            )

            timestamp = match.get(
                "timestamp",
                0.0
            )

            print(
                f"{index}. "
                f"{status} | "
                f"Track {track_id} | "
                f"{class_name} | "
                f"Ranking Score "
                f"{ranking_score:.4f} | "
                f"Best Similarity "
                f"{best_similarity:.4f} | "
                f"Time "
                f"{timestamp:.2f}s"
            )

    # --------------------------------------------------------
    # Output files
    # --------------------------------------------------------

    print("\nOUTPUT FILES")
    print("-" * 60)

    if files:

        for name, path in files.items():

            print(
                f"{name}: {path}"
            )

    else:

        print(
            "Output file information not available."
        )

    # --------------------------------------------------------
    # Result interpretation
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("RESULT INTERPRETATION")
    print("-" * 60)

    print(
        "The highest-ranked candidate is the strongest "
        "visual candidate identified by the ML pipeline."
    )

    print(
        "Similarity and ranking scores are not probability "
        "or identity-confidence values."
    )

    print(
        "Candidates are ranked using visual similarity "
        "and tracking observations."
    )

    print("\n" + "=" * 60)
    print("VISIONTRACE AI ML ENGINE FINISHED")
    print("=" * 60)


if __name__ == "__main__":
    main()