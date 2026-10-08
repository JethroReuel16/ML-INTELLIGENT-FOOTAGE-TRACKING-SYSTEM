import os
import re

from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


REFERENCE_IMAGE = "embedding/reference.jpg"
CROPS_FOLDER = "debug_crops"

MAX_CROPS = 50

CLASS_NAMES = {
    24: "backpack",
    26: "handbag",
    28: "suitcase",
}


def parse_filename(filename):
    pattern = r"frame_(\d+)_track_(\d+)_class_(\d+)\.jpg"

    match = re.match(pattern, filename)

    if not match:
        return None

    return {
        "frame": int(match.group(1)),
        "track": int(match.group(2)),
        "class_id": int(match.group(3)),
    }


def main():

    print("=" * 70)
    print("VISIONTRACE - CLEAN MATCHING EVALUATION")
    print("=" * 70)

    if not os.path.exists(REFERENCE_IMAGE):
        print(f"Reference image not found: {REFERENCE_IMAGE}")
        return

    if not os.path.exists(CROPS_FOLDER):
        print(f"Crops folder not found: {CROPS_FOLDER}")
        return

    # ---------------------------------------------------------
    # Find ONLY current-format crop files
    # ---------------------------------------------------------

    crop_files = []

    for filename in os.listdir(CROPS_FOLDER):

        if not filename.lower().endswith(".jpg"):
            continue

        info = parse_filename(filename)

        if info is not None:
            crop_files.append((filename, info))

    crop_files.sort(
        key=lambda item: item[1]["frame"]
    )

    if not crop_files:
        print("\nNo current-format crops found.")
        return

    crop_files = crop_files[:MAX_CROPS]

    print(f"\nCurrent-format crops found: {len(crop_files)}")

    # ---------------------------------------------------------
    # Load models
    # ---------------------------------------------------------

    print("\nLoading DINOv2...")

    extractor = DINOv2FeatureExtractor()

    print("\nLoading similarity engine...")

    similarity = SimilarityEngine()

    # ---------------------------------------------------------
    # Reference embedding
    # ---------------------------------------------------------

    print("\nGenerating reference embedding...")

    reference_embedding = extractor.extract(
        REFERENCE_IMAGE
    )

    # ---------------------------------------------------------
    # Evaluate
    # ---------------------------------------------------------

    results = []

    print("\n" + "-" * 70)
    print("EVALUATING CURRENT VIDEO CROPS")
    print("-" * 70)

    for index, (filename, info) in enumerate(
        crop_files,
        start=1
    ):

        path = os.path.join(
            CROPS_FOLDER,
            filename
        )

        print(
            f"[{index}/{len(crop_files)}] "
            f"{filename}"
        )

        try:

            candidate_embedding = extractor.extract(
                path
            )

            score = similarity.cosine_similarity(
                reference_embedding,
                candidate_embedding
            )

            results.append({
                "filename": filename,
                "frame": info["frame"],
                "track": info["track"],
                "class_id": info["class_id"],
                "score": score,
            })

        except Exception as error:

            print(
                f"ERROR: {error}"
            )

    # ---------------------------------------------------------
    # Sort
    # ---------------------------------------------------------

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # ---------------------------------------------------------
    # All results
    # ---------------------------------------------------------

    print("\n\n" + "=" * 70)
    print("RANKED CURRENT CROPS")
    print("=" * 70)

    print(
        f"{'Rank':<6}"
        f"{'Score':<12}"
        f"{'Frame':<8}"
        f"{'Track':<8}"
        f"{'Class':<12}"
        f"Filename"
    )

    print("-" * 70)

    for rank, result in enumerate(
        results,
        start=1
    ):

        class_name = CLASS_NAMES.get(
            result["class_id"],
            "unknown"
        )

        print(
            f"{rank:<6}"
            f"{result['score']:<12.6f}"
            f"{result['frame']:<8}"
            f"{result['track']:<8}"
            f"{class_name:<12}"
            f"{result['filename']}"
        )

    # ---------------------------------------------------------
    # Group by class
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("BEST SCORE BY OBJECT CLASS")
    print("=" * 70)

    for class_id, class_name in CLASS_NAMES.items():

        class_results = [
            r for r in results
            if r["class_id"] == class_id
        ]

        if not class_results:
            continue

        best = max(
            class_results,
            key=lambda x: x["score"]
        )

        average = sum(
            r["score"]
            for r in class_results
        ) / len(class_results)

        print(
            f"\n{class_name.upper()} "
            f"(class {class_id})"
        )

        print(
            f"Candidates : {len(class_results)}"
        )

        print(
            f"Best score : {best['score']:.6f}"
        )

        print(
            f"Average    : {average:.6f}"
        )

        print(
            f"Best crop  : {best['filename']}"
        )

    # ---------------------------------------------------------
    # Top 10
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("TOP 10 CURRENT CANDIDATES")
    print("=" * 70)

    for rank, result in enumerate(
        results[:10],
        start=1
    ):

        class_name = CLASS_NAMES.get(
            result["class_id"],
            "unknown"
        )

        print(
            f"\n{rank}. {result['filename']}"
        )

        print(
            f"   Similarity : {result['score']:.6f}"
        )

        print(
            f"   Frame      : {result['frame']}"
        )

        print(
            f"   Track      : {result['track']}"
        )

        print(
            f"   Class      : "
            f"{class_name} ({result['class_id']})"
        )

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()