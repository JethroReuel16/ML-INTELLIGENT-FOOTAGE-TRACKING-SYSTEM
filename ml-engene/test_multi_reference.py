import os
from PIL import Image, ImageEnhance

from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


REFERENCE_IMAGE = "embedding/reference.jpg"

TRACK_CROPS = [
    "debug_crops/frame_320_track_26_class_26.jpg",
    "debug_crops/frame_325_track_26_class_26.jpg",
    "debug_crops/frame_330_track_26_class_26.jpg",
    "debug_crops/frame_335_track_26_class_26.jpg",
    "debug_crops/frame_340_track_26_class_26.jpg",
    "debug_crops/frame_345_track_26_class_26.jpg",
]


def create_reference_variants(image_path):
    image = Image.open(image_path).convert("RGB")

    variants = {}

    # 1. Original
    variants["original"] = image

    # 2. Slight crop
    width, height = image.size

    crop_x = int(width * 0.05)
    crop_y = int(height * 0.05)

    if width > 2 * crop_x and height > 2 * crop_y:
        variants["cropped"] = image.crop(
            (
                crop_x,
                crop_y,
                width - crop_x,
                height - crop_y,
            )
        )

    # 3. Slight zoom
    zoom_x = int(width * 0.10)
    zoom_y = int(height * 0.10)

    if width > 2 * zoom_x and height > 2 * zoom_y:
        zoomed = image.crop(
            (
                zoom_x,
                zoom_y,
                width - zoom_x,
                height - zoom_y,
            )
        )

        zoomed = zoomed.resize(
            image.size,
            Image.Resampling.LANCZOS
        )

        variants["zoomed"] = zoomed

    # 4. Slight brightness increase
    variants["brighter"] = ImageEnhance.Brightness(
        image
    ).enhance(1.15)

    # 5. Slight brightness decrease
    variants["darker"] = ImageEnhance.Brightness(
        image
    ).enhance(0.85)

    return variants


def main():

    print("=" * 70)
    print("VISIONTRACE AI - MULTI-REFERENCE EXPERIMENT")
    print("=" * 70)

    print("\nLoading DINOv2...")

    extractor = DINOv2FeatureExtractor()
    similarity = SimilarityEngine()

    print("\nCreating reference variants...")

    reference_variants = create_reference_variants(
        REFERENCE_IMAGE
    )

    print(
        f"Created {len(reference_variants)} reference variants:"
    )

    for name in reference_variants:
        print(f"  - {name}")

    print("\nExtracting reference embeddings...")

    reference_embeddings = {}

    for name, image in reference_variants.items():

        embedding = extractor.extract(image)

        reference_embeddings[name] = embedding

        print(
            f"{name:12s} -> embedding created"
        )

    print("\nLoading Track 26 crops...")

    existing_crops = []

    for crop_path in TRACK_CROPS:

        if os.path.exists(crop_path):
            existing_crops.append(crop_path)
        else:
            print(
                f"WARNING: Missing crop: {crop_path}"
            )

    if not existing_crops:
        print("\nNo Track 26 crops found.")
        return

    print(
        f"\nFound {len(existing_crops)} Track 26 crops."
    )

    print("\n" + "=" * 70)
    print("REFERENCE-TO-VIDEO COMPARISON")
    print("=" * 70)

    all_results = []

    for crop_path in existing_crops:

        print("\n" + "-" * 70)

        print(
            f"Crop: {os.path.basename(crop_path)}"
        )

        crop_image = Image.open(
            crop_path
        ).convert("RGB")

        crop_embedding = extractor.extract(
            crop_image
        )

        crop_results = {}

        for name, reference_embedding in reference_embeddings.items():

            score = similarity.cosine_similarity(
                reference_embedding,
                crop_embedding
            )

            crop_results[name] = score

            print(
                f"{name:12s} -> {score:.6f}"
            )

        best_reference = max(
            crop_results,
            key=crop_results.get
        )

        best_score = crop_results[
            best_reference
        ]

        average_score = (
            sum(crop_results.values())
            / len(crop_results)
        )

        print(
            f"\nBEST REFERENCE: {best_reference}"
        )

        print(
            f"BEST SCORE:     {best_score:.6f}"
        )

        print(
            f"AVERAGE SCORE:  {average_score:.6f}"
        )

        all_results.append({
            "crop": os.path.basename(crop_path),
            "best_reference": best_reference,
            "best_score": best_score,
            "average_score": average_score,
            "scores": crop_results,
        })

    print("\n" + "=" * 70)
    print("FINAL MULTI-REFERENCE RESULTS")
    print("=" * 70)

    print(
        "\nCrop                                      "
        "Best Ref       Best Score     Average"
    )

    print("-" * 70)

    for result in all_results:

        print(
            f"{result['crop']:40s} "
            f"{result['best_reference']:12s} "
            f"{result['best_score']:.6f}       "
            f"{result['average_score']:.6f}"
        )

    best_overall = max(
        all_results,
        key=lambda x: x["best_score"]
    )

    print("\n" + "=" * 70)
    print("BEST OVERALL RESULT")
    print("=" * 70)

    print(
        f"Crop:           {best_overall['crop']}"
    )

    print(
        f"Reference:      {best_overall['best_reference']}"
    )

    print(
        f"Best similarity: {best_overall['best_score']:.6f}"
    )

    print(
        f"Average score:   {best_overall['average_score']:.6f}"
    )


if __name__ == "__main__":
    main()