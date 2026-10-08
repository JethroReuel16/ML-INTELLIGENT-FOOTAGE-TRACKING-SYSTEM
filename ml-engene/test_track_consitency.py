from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


IMAGE_A = "debug_crops/frame_0_track_6_class_28.jpg"
IMAGE_B = "debug_crops/frame_5_track_6_class_28.jpg"


def main():
    print("=" * 60)
    print("VISIONTRACE - TRACK CONSISTENCY TEST")
    print("=" * 60)

    extractor = DINOv2FeatureExtractor()
    similarity = SimilarityEngine()

    print("\nGenerating embedding for frame 0...")
    embedding_a = extractor.extract(IMAGE_A)

    print("Generating embedding for frame 5...")
    embedding_b = extractor.extract(IMAGE_B)

    score = similarity.cosine_similarity(
        embedding_a,
        embedding_b
    )

    print("\n" + "=" * 60)
    print("TRACK CONSISTENCY RESULT")
    print("=" * 60)
    print(f"Image A: {IMAGE_A}")
    print(f"Image B: {IMAGE_B}")
    print(f"Similarity: {score:.6f}")
    print("=" * 60)


if __name__ == "__main__":
    main()