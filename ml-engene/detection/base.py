"""Detector abstraction shared by every detection model."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Sequence, Set


class DetectorCapabilityError(ValueError):
    """The active detector cannot serve the requested search mode."""


class BaseDetector(ABC):
    """
    Contract every detector must satisfy so the pipeline, ByteTrack, the
    embedding stage and evidence generation never depend on a model.

    detect() returns a list of dicts:
        {"class_id": int, "class_name": str,
         "confidence": float, "bbox": [x1, y1, x2, y2]}
    """

    name = "base"
    checkpoint = None
    kind = "legacy"  # "legacy" (fixed classes) | "open_vocabulary"
    supports_text_prompts = False
    supports_visual_prompts = False

    @abstractmethod
    def detect(self, frame) -> List[Dict]:
        ...

    @abstractmethod
    def class_name(self, class_id: int) -> str:
        ...

    def configure_search(
        self,
        text_prompts: Optional[Sequence[str]] = None,
        reference_image=None,
        confidence: Optional[float] = None,
    ) -> Optional[Set[int]]:
        """
        Prepare the detector for one search.

        Returns the set of class IDs that should be kept, or None when
        every detection class is relevant.
        """
        if text_prompts:
            raise DetectorCapabilityError(
                f"The active detector '{self.name}' does not support text "
                "prompts. Set DETECTOR_MODEL=yoloe to enable them."
            )
        return None

    def info(self) -> Dict:
        return {
            "name": self.name,
            "checkpoint": self.checkpoint,
            "kind": self.kind,
            "supports_text_prompts": self.supports_text_prompts,
            "supports_visual_prompts": self.supports_visual_prompts,
        }
