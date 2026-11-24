import logging

from ml_config import LEGACY_ALLOWED_CLASSES
from detection.base import BaseDetector


logger = logging.getLogger(__name__)


class YOLODetector(BaseDetector):
    """Legacy fixed-class detector (Ultralytics YOLO11n, COCO classes)."""

    name = "yolo11n"
    kind = "legacy"

    def __init__(
        self,
        model_path="yolo11n.pt",
        device="cpu",
        confidence=0.25,
        imgsz=640,
        allowed_classes=LEGACY_ALLOWED_CLASSES,
    ):
        from ultralytics import YOLO

        logger.info("Loading YOLO model (%s)...", model_path)
        self.checkpoint = model_path
        self.device = device
        self.confidence = confidence
        self.imgsz = imgsz
        self.allowed_classes = set(allowed_classes)
        self.model = YOLO(model_path)
        logger.info("YOLO model loaded.")

    def class_name(self, class_id):
        names = self.model.names

        if isinstance(names, dict):
            return names.get(class_id, f"class_{class_id}")

        if 0 <= class_id < len(names):
            return names[class_id]

        return f"class_{class_id}"

    def configure_search(
        self,
        text_prompts=None,
        reference_image=None,
        confidence=None,
    ):
        # Raises DetectorCapabilityError when text prompts are supplied.
        super().configure_search(text_prompts, reference_image, confidence)

        if confidence is not None:
            self.confidence = confidence

        return set(self.allowed_classes)

    def detect(self, frame):
        results = self.model(
            frame,
            conf=self.confidence,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
        )

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
