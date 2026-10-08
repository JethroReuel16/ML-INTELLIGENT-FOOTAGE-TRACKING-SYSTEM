import torch
import torch.nn.functional as F


class SimilarityEngine:

    def __init__(self):
        print("Similarity engine initialized.")

    def cosine_similarity(
        self,
        embedding_a,
        embedding_b
    ):

        # Make sure both embeddings are tensors
        if not isinstance(embedding_a, torch.Tensor):
            embedding_a = torch.tensor(embedding_a)

        if not isinstance(embedding_b, torch.Tensor):
            embedding_b = torch.tensor(embedding_b)

        # Add batch dimension
        embedding_a = embedding_a.unsqueeze(0)
        embedding_b = embedding_b.unsqueeze(0)

        # Calculate cosine similarity
        similarity = F.cosine_similarity(
            embedding_a,
            embedding_b
        )

        return float(similarity.item())


if __name__ == "__main__":

    print("=" * 50)
    print("VISIONTRACE AI - SIMILARITY TEST")
    print("=" * 50)

    engine = SimilarityEngine()

    # Example embeddings
    embedding_a = torch.tensor(
        [1.0, 2.0, 3.0]
    )

    embedding_b = torch.tensor(
        [1.0, 2.0, 3.0]
    )

    score = engine.cosine_similarity(
        embedding_a,
        embedding_b
    )

    print("\nSimilarity score:", score)