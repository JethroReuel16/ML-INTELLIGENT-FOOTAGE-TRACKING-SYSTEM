import os
import re

from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


REFERENCE_IMAGE = "embedding/reference.jpg"
CROPS_FOLDER = "debug_crops"

# Maximum number of crops to test
MAX_CROPS = 20


def extract_crop_info(filename):
    """
    Extract information from filenames such as:

    frame_0_track_6_class_28.jpg
    frame_225_track_30_class_26.jpg
    """

    pattern = r"frame_(\d+)_track_(\d+)_class_(\d+)\.jpg"

    match = re.match(pattern, filename)

    if match:
        frame_number = int(match.group(1))
        track_id = int(match.group(2))
        class_id = int(match.group(3))

        return {
            "frame_number": frame_number,
            "track_id": track_id,
            "class_id": class_id,
        }

    return {
        "frame_number": None,
        "track_id": None,
        "class_id": None,
    }


def main():

    print("=" * 70)
    print("VISIONTRACE - MATCHING EVALUATION")
    print("=" * 70)

    # ---------------------------------------------------------
    # Check reference image
    # ---------------------------------------------------------

    if not os.path.exists(REFERENCE_IMAGE):
        print(f"\nERROR: Reference image not found:")
        print(REFERENCE_IMAGE)
        return

    # ---------------------------------------------------------
    # Check crops folder
    # ---------------------------------------------------------

    if not os.path.exists(CROPS_FOLDER):
        print(f"\nERROR: Crops folder not found:")
        print(CROPS_FOLDER)
        return

    # ---------------------------------------------------------
    # Find crop images
    # ---------------------------------------------------------

    crop_files = [
        filename
        for filename in os.listdir(CROPS_FOLDER)
        if filename.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not crop_files:
        print("\nERROR: No crop images found.")
        return

    # Sort filenames naturally by frame number
    crop_files.sort()

    # Limit to MAX_CROPS
    crop_files = crop_files[:MAX_CROPS]

    print(f"\nReference image:")
    print(f"  {REFERENCE_IMAGE}")

    print(f"\nCrops folder:")
    print(f"  {CROPS_FOLDER}")

    print(f"\nCrops selected for evaluation: {len(crop_files)}")

    # ---------------------------------------------------------
    # Load models
    # ---------------------------------------------------------

    print("\n" + "-" * 70)
    print("LOADING MODELS")
    print("-" * 70)

    extractor = DINOv2FeatureExtractor()
    similarity = SimilarityEngine()

    # ---------------------------------------------------------
    # Generate reference embedding
    # ---------------------------------------------------------

    print("\nGenerating reference embedding...")

    reference_embedding = extractor.extract(
        REFERENCE_IMAGE
    )

    print("Reference embedding generated.")

    # ---------------------------------------------------------
    # Evaluate crops
    # ---------------------------------------------------------

    results = []

    print("\n" + "-" * 70)
    print("EVALUATING CROPS")
    print("-" * 70)

    for index, filename in enumerate(crop_files, start=1):

        crop_path = os.path.join(
            CROPS_FOLDER,
            filename
        )

        print(
            f"\n[{index}/{len(crop_files)}] "
            f"Processing {filename}..."
        )

        try:

            crop_embedding = extractor.extract(
                crop_path
            )

            score = similarity.cosine_similarity(
                reference_embedding,
                crop_embedding
            )

            info = extract_crop_info(filename)

            results.append({
                "filename": filename,
                "similarity": score,
                "frame_number": info["frame_number"],
                "track_id": info["track_id"],
                "class_id": info["class_id"],
            })

            print(
                f"Similarity: {score:.6f}"
            )

        except Exception as error:

            print(
                f"ERROR processing {filename}: {error}"
            )

    # ---------------------------------------------------------
    # Sort highest similarity first
    # ---------------------------------------------------------

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    # ---------------------------------------------------------
    # Display results
    # ---------------------------------------------------------

    print("\n\n" + "=" * 70)
    print("MATCHING EVALUATION RESULTS")
    print("=" * 70)

    if not results:
        print("\nNo results were generated.")
        return

    print(
        f"\n{'Rank':<6}"
        f"{'Score':<12}"
        f"{'Frame':<10}"
        f"{'Track':<10}"
        f"{'Class':<10}"
        f"Filename"
    )

    print("-" * 70)

    for rank, result in enumerate(results, start=1):

        frame = (
            str(result["frame_number"])
            if result["frame_number"] is not None
            else "-"
        )

        track = (
            str(result["track_id"])
            if result["track_id"] is not None
            else "-"
        )

        class_id = (
            str(result["class_id"])
            if result["class_id"] is not None
            else "-"
        )

        print(
            f"{rank:<6}"
            f"{result['similarity']:<12.6f}"
            f"{frame:<10}"
            f"{track:<10}"
            f"{class_id:<10}"
            f"{result['filename']}"
        )

    # ---------------------------------------------------------
    # Top 5
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("TOP 5 CANDIDATES")
    print("=" * 70)

    for rank, result in enumerate(results[:5], start=1):

        print(
            f"\n{rank}. {result['filename']}"
        )

        print(
            f"   Similarity : "
            f"{result['similarity']:.6f}"
        )

        print(
            f"   Frame      : "
            f"{result['frame_number']}"
        )

        print(
            f"   Track ID   : "
            f"{result['track_id']}"
        )

        print(
            f"   Class ID   : "
            f"{result['class_id']}"
        )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    scores = [
        result["similarity"]
        for result in results
    ]

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"Candidates tested : {len(results)}")
    print(f"Highest score     : {max(scores):.6f}")
    print(f"Lowest score      : {min(scores):.6f}")
    print(
        f"Average score     : "
        f"{sum(scores) / len(scores):.6f}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()