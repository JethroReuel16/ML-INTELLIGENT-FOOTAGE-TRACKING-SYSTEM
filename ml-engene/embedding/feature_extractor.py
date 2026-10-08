import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel


class DINOv2FeatureExtractor:

    def __init__(self):

        print("Loading DINOv2 model...")

        self.device = torch.device("cpu")

        self.processor = AutoImageProcessor.from_pretrained(
            "facebook/dinov2-base"
        )

        self.model = AutoModel.from_pretrained(
            "facebook/dinov2-base"
        )

        self.model.to(self.device)

        self.model.eval()

        print("DINOv2 model loaded.")
        print("Device:", self.device)

    def extract(self, image):

        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        else:
            image = image.convert("RGB")

        inputs = self.processor(
            images=image,
            return_tensors="pt"
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        with torch.no_grad():

            outputs = self.model(**inputs)

        embedding = outputs.last_hidden_state[:, 0, :]

        embedding = embedding.squeeze(0)

        embedding = embedding / embedding.norm()

        return embedding


if __name__ == "__main__":

    print("=" * 50)
    print("VISIONTRACE AI - DINOV2 EMBEDDING TEST")
    print("=" * 50)

    extractor = DINOv2FeatureExtractor()

    image_path = "test_image.jpg"

    print("\nExtracting features...")

    embedding = extractor.extract(image_path)

    print("\nEmbedding generated successfully.")

    print("Embedding shape:", embedding.shape)

    print("Embedding dimensions:", embedding.numel())

    print("First 10 values:")
    print(embedding[:10])