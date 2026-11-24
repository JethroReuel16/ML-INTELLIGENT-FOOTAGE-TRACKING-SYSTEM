import torch
import torch.nn.functional as F


class SimilarityEngine:
    """Cosine similarity between DINOv2 embeddings."""

    def cosine_similarity(self, embedding_a, embedding_b):
        if not isinstance(embedding_a, torch.Tensor):
            embedding_a = torch.tensor(embedding_a)
        if not isinstance(embedding_b, torch.Tensor):
            embedding_b = torch.tensor(embedding_b)

        return float(F.cosine_similarity(embedding_a.unsqueeze(0), embedding_b.unsqueeze(0)).item())

    def cosine_similarity_many(self, reference, embeddings):
        """Similarity of one reference [D] against many embeddings [N, D] -> list of floats."""
        if not isinstance(reference, torch.Tensor):
            reference = torch.tensor(reference)
        if not isinstance(embeddings, torch.Tensor):
            embeddings = torch.as_tensor(embeddings)
        if embeddings.numel() == 0:
            return []

        return F.cosine_similarity(embeddings, reference.unsqueeze(0).to(embeddings.dtype), dim=-1).tolist()
