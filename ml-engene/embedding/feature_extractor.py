import logging

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

logger = logging.getLogger(__name__)


class DINOv2FeatureExtractor:
    """DINOv2 CLS-token embeddings, L2-normalised."""

    def __init__(self, model_name="facebook/dinov2-base", device="cpu", batch_size=16):
        logger.info("Loading DINOv2 model (%s)...", model_name)

        try:
            self.device = torch.device(device)
        except (RuntimeError, TypeError):
            logger.warning("Invalid DINO device %r; using CPU.", device)
            self.device = torch.device("cpu")

        self.batch_size = max(1, int(batch_size))
        self.processor, self.model = self._load(model_name)
        self.model.to(self.device)
        self.model.eval()

        logger.info("DINOv2 model loaded on %s.", self.device)

    @staticmethod
    def _load(model_name):
        """
        Load from the local Hugging Face cache first; only go online when the
        model is not cached yet. Avoids slow update checks (and rate-limit
        warnings) on every start-up.
        """
        try:
            return (
                AutoImageProcessor.from_pretrained(model_name, local_files_only=True),
                AutoModel.from_pretrained(model_name, local_files_only=True),
            )
        except OSError:
            logger.info("%s is not cached yet; downloading from Hugging Face...", model_name)
            return (
                AutoImageProcessor.from_pretrained(model_name),
                AutoModel.from_pretrained(model_name),
            )

    @staticmethod
    def _to_rgb(image):
        if isinstance(image, str):
            with Image.open(image) as handle:
                return handle.convert("RGB")
        return image.convert("RGB")

    def extract_batch(self, images):
        """Embed several images in as few forward passes as possible -> [N, D] tensor."""
        if not images:
            return torch.empty(0)

        rgb = [self._to_rgb(image) for image in images]
        outputs = []

        with torch.inference_mode():
            for start in range(0, len(rgb), self.batch_size):
                chunk = rgb[start:start + self.batch_size]
                inputs = self.processor(images=chunk, return_tensors="pt")
                inputs = {key: value.to(self.device) for key, value in inputs.items()}
                cls = self.model(**inputs).last_hidden_state[:, 0, :]
                outputs.append(torch.nn.functional.normalize(cls, dim=-1).cpu())

        return torch.cat(outputs, dim=0)

    def extract(self, image):
        """Embed one image -> [D] tensor."""
        return self.extract_batch([image])[0]
