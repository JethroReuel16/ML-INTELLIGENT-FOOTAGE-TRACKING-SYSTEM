from embedding.feature_extractor import DINOv2FeatureExtractor
from matching.similarity import SimilarityEngine


IMAGE = "embedding/reference.jpg"


def main():

    print("=" * 60)
    print("VISIONTRACE - SELF MATCH TEST")
    print("=" * 60)

    extractor = DINOv2FeatureExtractor()
    similarity = SimilarityEngine()

    print("\nGenerating first embedding...")

    embedding_a = extractor.extract(
        IMAGE
    )

    print("First embedding generated.")

    print("\nGenerating second embedding...")

    embedding_b = extractor.extract(
        IMAGE
    )

    print("Second embedding generated.")

    score = similarity.cosine_similarity(
        embedding_a,
        embedding_b
    )

    print("\n" + "=" * 60)
    print("SELF MATCH RESULT")
    print("=" * 60)

    print(
        f"Similarity: {score:.6f}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()