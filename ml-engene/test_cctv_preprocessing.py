import os

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

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


def create_cctv_variants(image):
    """
    Create controlled preprocessing variants of a CCTV crop.
    """

    image = image.convert("RGB")

    variants = {}

    # 1. Original
    variants["original"] = image

    # 2. Resize
    variants["resized"] = image.resize(
        (224, 224),
        Image.Resampling.LANCZOS
    )

    # 3. Slightly brighter
    variants["brighter"] = ImageEnhance.Brightness(
        image
    ).enhance(1.15)

    # 4. Slightly darker
    variants["darker"] = ImageEnhance.Brightness(
        image
    ).enhance(0.85)

    # 5. Increased contrast
    variants["contrast"] = ImageEnhance.Contrast(
        image
    ).enhance(1.25)

    # 6. Reduced contrast
    variants["low_contrast"] = ImageEnhance.Contrast(
        image
    ).enhance(0.80)

    # 7. Sharpened
    variants["sharpened"] = image.filter(
        ImageFilter.SHARPEN
    )

    # 8. Stronger sharpening
    variants["strong_sharpen"] = image.filter(
        ImageFilter.UnsharpMask(
            radius=2,
            percent=150,
            threshold=3
        )
    )

    # 9. Grayscale converted back to RGB
    grayscale = ImageOps.grayscale(image)
    variants["grayscale"] = grayscale.convert("RGB")

    # 10. Brightness + contrast
    enhanced = ImageEnhance.Brightness(
        image
    ).enhance(1.10)

    enhanced = ImageEnhance.Contrast(
        enhanced
    ).enhance(1.20)

    variants["brightness_contrast"] = enhanced

    return variants


def main():

    print("=" * 70)
    print("VISIONTRACE AI - CCTV PREPROCESSING EXPERIMENT")
    print("=" * 70)

    # ---------------------------------------------------------
    # LOAD MODELS
    # ---------------------------------------------------------

    print("\nLoading DINOv2...")

    extractor = DINOv2FeatureExtractor()
    similarity = SimilarityEngine()

    # ---------------------------------------------------------
    # REFERENCE
    # ---------------------------------------------------------

    print("\nLoading reference image...")

    reference_image = Image.open(
        REFERENCE_IMAGE
    ).convert("RGB")

    reference_embedding = extractor.extract(
        reference_image
    )

    print("Reference embedding created.")

    # ---------------------------------------------------------
    # LOAD CROPS
    # ---------------------------------------------------------

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
        f"Found {len(existing_crops)} Track 26 crops."
    )

    # ---------------------------------------------------------
    # PROCESS EACH CROP
    # ---------------------------------------------------------

    all_results = []

    for crop_path in existing_crops:

        print("\n" + "-" * 70)

        crop_name = os.path.basename(crop_path)

        print(f"Crop: {crop_name}")

        image = Image.open(
            crop_path
        ).convert("RGB")

        variants = create_cctv_variants(
            image
        )

        crop_results = {}

        for variant_name, variant_image in variants.items():

            embedding = extractor.extract(
                variant_image
            )

            score = similarity.cosine_similarity(
                reference_embedding,
                embedding
            )

            crop_results[variant_name] = score

            print(
                f"{variant_name:20s} -> {score:.6f}"
            )

        # -----------------------------------------------------
        # BEST VARIANT
        # -----------------------------------------------------

        best_variant = max(
            crop_results,
            key=crop_results.get
        )

        best_score = crop_results[
            best_variant
        ]

        average_score = (
            sum(crop_results.values())
            / len(crop_results)
        )

        print(
            f"\nBEST VARIANT:  {best_variant}"
        )

        print(
            f"BEST SCORE:    {best_score:.6f}"
        )

        print(
            f"AVERAGE SCORE: {average_score:.6f}"
        )

        all_results.append({
            "crop": crop_name,
            "best_variant": best_variant,
            "best_score": best_score,
            "average_score": average_score,
            "scores": crop_results,
        })

    # ---------------------------------------------------------
    # FINAL SUMMARY
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL PREPROCESSING RESULTS")
    print("=" * 70)

    print(
        "\nCrop                                      "
        "Best Variant          Best Score"
    )

    print("-" * 70)

    for result in all_results:

        print(
            f"{result['crop']:40s} "
            f"{result['best_variant']:20s} "
            f"{result['best_score']:.6f}"
        )

    # ---------------------------------------------------------
    # FIND BEST OVERALL RESULT
    # ---------------------------------------------------------

    best_overall = max(
        all_results,
        key=lambda x: x["best_score"]
    )

    print("\n" + "=" * 70)
    print("BEST OVERALL RESULT")
    print("=" * 70)

    print(
        f"Crop:            "
        f"{best_overall['crop']}"
    )

    print(
        f"Preprocessing:   "
        f"{best_overall['best_variant']}"
    )

    print(
        f"Best similarity: "
        f"{best_overall['best_score']:.6f}"
    )

    # ---------------------------------------------------------
    # COMPARE AGAINST BASELINE
    # ---------------------------------------------------------

    baseline = 0.340414

    improvement = (
        best_overall["best_score"]
        - baseline
    )

    percentage_change = (
        improvement / baseline
    ) * 100

    print("\n" + "=" * 70)
    print("BASELINE COMPARISON")
    print("=" * 70)

    print(
        f"Previous best:     {baseline:.6f}"
    )

    print(
        f"New best:          "
        f"{best_overall['best_score']:.6f}"
    )

    print(
        f"Difference:        "
        f"{improvement:+.6f}"
    )

    print(
        f"Percentage change: "
        f"{percentage_change:+.2f}%"
    )


if __name__ == "__main__":
    main()