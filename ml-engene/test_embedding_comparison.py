from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


REFERENCE_IMAGE = "embedding/reference.jpg"

TRACK_26_FRAMES = {
    320: "debug_crops/frame_320_track_26_class_26.jpg",
    325: "debug_crops/frame_325_track_26_class_26.jpg",
    330: "debug_crops/frame_330_track_26_class_26.jpg",
    335: "debug_crops/frame_335_track_26_class_26.jpg",
    340: "debug_crops/frame_340_track_26_class_26.jpg",
    345: "debug_crops/frame_345_track_26_class_26.jpg",
}


def main():

    print("=" * 75)
    print("VISIONTRACE AI - TRACK 26 EMBEDDING ANALYSIS")
    print("=" * 75)

    # ---------------------------------------------------------
    # LOAD MODELS
    # ---------------------------------------------------------

    print("\nLoading DINOv2...")
    extractor = DINOv2FeatureExtractor()

    print("\nLoading similarity engine...")
    similarity = SimilarityEngine()

    # ---------------------------------------------------------
    # REFERENCE EMBEDDING
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("REFERENCE EMBEDDING")
    print("=" * 75)

    print(f"\nReference: {REFERENCE_IMAGE}")

    reference_embedding = extractor.extract(
        REFERENCE_IMAGE
    )

    print("Reference embedding created.")

    # ---------------------------------------------------------
    # CREATE FRAME EMBEDDINGS
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("CREATING TRACK 26 EMBEDDINGS")
    print("=" * 75)

    embeddings = {}

    for frame_number, image_path in TRACK_26_FRAMES.items():

        print(
            f"\nFrame {frame_number}: "
            f"{image_path}"
        )

        embeddings[frame_number] = extractor.extract(
            image_path
        )

        print(
            f"Embedding created for frame {frame_number}."
        )

    # ---------------------------------------------------------
    # REFERENCE -> EACH FRAME
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("REFERENCE -> TRACK 26")
    print("=" * 75)

    reference_scores = []

    for frame_number, embedding in embeddings.items():

        score = similarity.cosine_similarity(
            reference_embedding,
            embedding
        )

        reference_scores.append(
            (frame_number, score)
        )

        print(
            f"Reference -> Frame {frame_number}: "
            f"{score:.6f}"
        )

    # ---------------------------------------------------------
    # SORT REFERENCE SCORES
    # ---------------------------------------------------------

    reference_scores.sort(
        key=lambda item: item[1],
        reverse=True
    )

    print("\n" + "-" * 75)
    print("REFERENCE RANKING")
    print("-" * 75)

    for rank, (frame_number, score) in enumerate(
        reference_scores,
        start=1
    ):
        print(
            f"{rank}. "
            f"Frame {frame_number} -> "
            f"{score:.6f}"
        )

    # ---------------------------------------------------------
    # FRAME-TO-FRAME COMPARISON
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("FRAME-TO-FRAME SIMILARITY")
    print("=" * 75)

    frame_numbers = list(
        TRACK_26_FRAMES.keys()
    )

    pair_scores = []

    for i in range(len(frame_numbers)):

        frame_a = frame_numbers[i]

        for j in range(i + 1, len(frame_numbers)):

            frame_b = frame_numbers[j]

            score = similarity.cosine_similarity(
                embeddings[frame_a],
                embeddings[frame_b]
            )

            pair_scores.append(
                (frame_a, frame_b, score)
            )

            print(
                f"Frame {frame_a} -> "
                f"Frame {frame_b}: "
                f"{score:.6f}"
            )

    # ---------------------------------------------------------
    # FRAME CONSISTENCY SUMMARY
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("FRAME CONSISTENCY SUMMARY")
    print("=" * 75)

    pair_values = [
        score
        for _, _, score in pair_scores
    ]

    if pair_values:

        minimum_pair = min(pair_scores, key=lambda x: x[2])
        maximum_pair = max(pair_scores, key=lambda x: x[2])

        average_pair = (
            sum(pair_values)
            / len(pair_values)
        )

        print(
            f"\nLowest frame-to-frame similarity: "
            f"Frame {minimum_pair[0]} -> "
            f"Frame {minimum_pair[1]} = "
            f"{minimum_pair[2]:.6f}"
        )

        print(
            f"Highest frame-to-frame similarity: "
            f"Frame {maximum_pair[0]} -> "
            f"Frame {maximum_pair[1]} = "
            f"{maximum_pair[2]:.6f}"
        )

        print(
            f"Average frame-to-frame similarity: "
            f"{average_pair:.6f}"
        )

    # ---------------------------------------------------------
    # REFERENCE SCORE SUMMARY
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("REFERENCE SCORE SUMMARY")
    print("=" * 75)

    reference_values = [
        score
        for _, score in reference_scores
    ]

    if reference_values:

        best_reference = max(
            reference_values
        )

        worst_reference = min(
            reference_values
        )

        average_reference = (
            sum(reference_values)
            / len(reference_values)
        )

        print(
            f"\nBest reference similarity: "
            f"{best_reference:.6f}"
        )

        print(
            f"Worst reference similarity: "
            f"{worst_reference:.6f}"
        )

        print(
            f"Average reference similarity: "
            f"{average_reference:.6f}"
        )

        print(
            f"Reference score range: "
            f"{best_reference - worst_reference:.6f}"
        )

    # ---------------------------------------------------------
    # FINAL INTERPRETATION
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("ANALYSIS")
    print("=" * 75)

    print(
        "\nThis experiment separates two questions:"
    )

    print(
        "\n1. Does DINOv2 recognize the same object "
        "across video frames?"
    )

    print(
        "2. Does DINOv2 recognize the CCTV object "
        "as similar to the reference image?"
    )

    print(
        "\nUse the reference ranking and frame-to-frame "
        "scores above to evaluate both."
    )

    print("\n" + "=" * 75)
    print("TEST COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()