from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


REFERENCE_IMAGE = "embedding/reference.jpg"
CANDIDATE_IMAGE = "embedding/candidate.jpg"


def main():

    print("=" * 60)
    print("VISIONTRACE AI - REAL IMAGE MATCHING TEST")
    print("=" * 60)

    # --------------------------------
    # Load DINOv2
    # --------------------------------

    extractor = DINOv2FeatureExtractor()

    # --------------------------------
    # Load similarity engine
    # --------------------------------

    similarity_engine = SimilarityEngine()

    # --------------------------------
    # Extract reference embedding
    # --------------------------------

    print("\nExtracting reference image features...")

    reference_embedding = extractor.extract(
        REFERENCE_IMAGE
    )

    print("Reference embedding generated.")

    # --------------------------------
    # Extract candidate embedding
    # --------------------------------

    print("\nExtracting candidate image features...")

    candidate_embedding = extractor.extract(
        CANDIDATE_IMAGE
    )

    print("Candidate embedding generated.")

    # --------------------------------
    # Calculate similarity
    # --------------------------------

    score = similarity_engine.cosine_similarity(
        reference_embedding,
        candidate_embedding
    )

    print("\n" + "=" * 60)
    print("MATCHING RESULT")
    print("=" * 60)

    print(f"Similarity score: {score:.4f}")

    print("=" * 60)


if __name__ == "__main__":
    main()