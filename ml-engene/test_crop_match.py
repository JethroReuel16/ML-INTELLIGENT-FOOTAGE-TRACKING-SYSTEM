from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


REFERENCE_IMAGE = "embedding/reference.jpg"
CANDIDATE_IMAGE = "debug_crops/frame_0_track_6_class_28.jpg"


def main():
    print("=" * 60)
    print("VISIONTRACE - REFERENCE VS CANDIDATE TEST")
    print("=" * 60)

    extractor = DINOv2FeatureExtractor()
    similarity = SimilarityEngine()

    print("\nGenerating reference embedding...")
    reference_embedding = extractor.extract(REFERENCE_IMAGE)

    print("Generating candidate embedding...")
    candidate_embedding = extractor.extract(CANDIDATE_IMAGE)

    score = similarity.cosine_similarity(
        reference_embedding,
        candidate_embedding
    )

    print("\n" + "=" * 60)
    print("MATCH RESULT")
    print("=" * 60)
    print(f"Reference: {REFERENCE_IMAGE}")
    print(f"Candidate: {CANDIDATE_IMAGE}")
    print(f"Similarity: {score:.6f}")
    print("=" * 60)


if __name__ == "__main__":
    main()