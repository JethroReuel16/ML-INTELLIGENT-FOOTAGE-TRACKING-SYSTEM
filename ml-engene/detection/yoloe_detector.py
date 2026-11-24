"""YOLOE open-vocabulary detector (Ultralytics)."""

import contextlib
import logging
import os
import warnings

from detection.base import BaseDetector, DetectorCapabilityError

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _quiet_torchscript():
    """
    YOLOE's text encoder (mobileclip_blt.ts) is TorchScript; PyTorch warns
    that torch.jit.load "may break" on Python 3.14+. It works with the pinned
    versions (verified by the test suite), so only that warning is hidden.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*torch\.jit\.load.*",
            category=FutureWarning,
        )
        yield


class YOLOEDetector(BaseDetector):
    """
    Text-prompted open-vocabulary detection.

    Text prompts: supported by every *-seg.pt checkpoint through
    model.set_classes(names). Class IDs are indexes into the active prompt
    list, which is what ByteTrack receives.

    Visual prompts (experimental, off by default): the reference image is
    used as `refer_image` with a whole-image box. Ultralytics re-computes the
    visual embedding on every call, so this is much slower, and it replaces
    the text classes permanently, so the text prompts are re-applied before
    the next search.

    Prompt-free (*-pf) checkpoints cannot be used here.
    """

    name = "yoloe"
    kind = "open_vocabulary"
    supports_text_prompts = True
    supports_visual_prompts = True

    def __init__(
        self,
        checkpoint="yoloe-11s-seg.pt",
        device="cpu",
        confidence=0.25,
        imgsz=640,
        default_categories=(),
        use_visual_prompt=False,
    ):
        if "-pf" in os.path.basename(checkpoint):
            raise DetectorCapabilityError(
                "Prompt-free YOLOE checkpoints do not support text or "
                "visual prompts. Use a *-seg.pt checkpoint."
            )

        from ultralytics import YOLOE

        logger.info("Loading YOLOE model (%s)...", checkpoint)
        self.checkpoint = checkpoint
        self.device = device
        self.confidence = confidence
        self.imgsz = imgsz
        self.default_categories = tuple(default_categories)
        self.use_visual_prompt = use_visual_prompt

        with _quiet_torchscript():
            self.model = YOLOE(checkpoint)
        self._prompts = ()
        self._reference = None  # (path, w, h) while visual prompting
        self._classes_dirty = False

        self._apply_text_prompts(self.default_categories)
        logger.info("YOLOE model loaded.")

    # ------------------------------------------------------------------
    def _apply_text_prompts(self, names):
        names = tuple(dict.fromkeys(n for n in names if n))

        if not names:
            raise DetectorCapabilityError("At least one text prompt is required.")

        if names == self._prompts and not self._classes_dirty:
            return  # same prompts as last search: skip text-encoder work

        with _quiet_torchscript():
            self.model.set_classes(list(names))
        self._prompts = names
        self._classes_dirty = False

    def class_name(self, class_id):
        if self._reference is not None:
            return "reference object"

        if 0 <= class_id < len(self._prompts):
            return self._prompts[class_id]

        return f"class_{class_id}"

    def configure_search(
        self,
        text_prompts=None,
        reference_image=None,
        confidence=None,
    ):
        if confidence is not None:
            self.confidence = confidence

        self._reference = None

        wants_visual = (
            self.use_visual_prompt
            and reference_image is not None
            and not text_prompts
        )

        if wants_visual:
            from PIL import Image

            with Image.open(reference_image) as image:
                width, height = image.size

            self._reference = (reference_image, width, height)
            self._classes_dirty = True  # refer_image overwrites the classes
            return None

        self._apply_text_prompts(
            tuple(text_prompts) if text_prompts else self.default_categories
        )

        return None  # every prompted class is relevant

    def detect(self, frame):
        kwargs = dict(
            conf=self.confidence,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
        )

        if self._reference is not None:
            import numpy as np

            path, width, height = self._reference
            kwargs["refer_image"] = path
            kwargs["visual_prompts"] = {
                "bboxes": np.array([[0, 0, width, height]], dtype=float),
                "cls": np.array([0]),
            }

        results = self.model.predict(frame, **kwargs)

        detections = []

        for result in results:
            boxes = result.boxes

            if boxes is None:
                continue

            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                class_id = int(box.cls[0])

                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": self.class_name(class_id),
                        "confidence": float(box.conf[0]),
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    }
                )

        return detections
