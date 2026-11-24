"""Lightweight stand-ins so the engine logic can be tested without
ultralytics / torch / supervision. They exercise OUR code paths; they are not
a substitute for running the real models (see tools/benchmark_detectors.py).
"""

import sys
import types

import cv2
import numpy as np

from detection.base import BaseDetector


# --------------------------------------------------------------------------
# Fake `ultralytics` package
# --------------------------------------------------------------------------

class _Tensor(list):
    def tolist(self):
        return list(self)


class _Box:
    def __init__(self, xyxy, conf, cls):
        self.xyxy = [_Tensor(xyxy)]
        self.conf = [conf]
        self.cls = [cls]


class _Result:
    def __init__(self, boxes):
        self.boxes = boxes


class FakeYOLOE:
    instances = []

    def __init__(self, checkpoint):
        self.checkpoint = checkpoint
        self.set_classes_calls = []
        self.predict_calls = []
        self.names = {}
        self.next_boxes = [([10, 20, 110, 220], 0.9, 0)]
        FakeYOLOE.instances.append(self)

    def set_classes(self, names):
        self.set_classes_calls.append(list(names))
        self.names = dict(enumerate(names))

    def predict(self, frame, **kwargs):
        self.predict_calls.append(kwargs)
        return [_Result([_Box(*b) for b in self.next_boxes])]


class FakeYOLO:
    def __init__(self, path):
        self.path = path
        self.names = {24: "backpack", 26: "handbag", 28: "suitcase"}
        self.call_kwargs = []

    def __call__(self, frame, **kwargs):
        self.call_kwargs.append(kwargs)
        return [_Result([_Box([5, 5, 50, 80], 0.8, 24)])]


def install_fake_ultralytics(yoloe_fails=False):
    module = types.ModuleType("ultralytics")

    if yoloe_fails:
        def broken(_):
            raise RuntimeError("weights could not be downloaded")

        module.YOLOE = broken
    else:
        module.YOLOE = FakeYOLOE

    module.YOLO = FakeYOLO
    sys.modules["ultralytics"] = module
    FakeYOLOE.instances.clear()
    return module


# --------------------------------------------------------------------------
# Synthetic video + colour-based fake detector / embedder
# --------------------------------------------------------------------------

RED = (0, 0, 255)    # BGR
BLUE = (255, 0, 0)

W, H, FPS, FRAMES = 320, 240, 10, 90


def make_video(path):
    """Red 'backpack' moves right the whole video; blue 'laptop' enters at
    frame 30 and moves left, leaving the frame at the end."""
    writer = cv2.VideoWriter(
        path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H)
    )

    for i in range(FRAMES):
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        x = 10 + i * 2
        cv2.rectangle(frame, (x, 40), (x + 40, 100), RED, -1)

        if i >= 30:
            bx = 250 - (i - 30) * 3
            cv2.rectangle(frame, (bx, 140), (bx + 60, 180), BLUE, -1)

        writer.write(frame)

    writer.release()
    return path


def make_reference(path, color):
    image = np.zeros((120, 120, 3), dtype=np.uint8)
    image[:] = color
    cv2.imwrite(path, image)
    return path


class ColorDetector(BaseDetector):
    """Open-vocabulary stand-in: finds red => 'backpack', blue => 'laptop',
    but only for the classes currently prompted."""

    name = "yoloe"
    checkpoint = "fake-yoloe-seg.pt"
    kind = "open_vocabulary"
    supports_text_prompts = True
    supports_visual_prompts = True

    LABELS = {"backpack": RED, "laptop": BLUE}

    def __init__(self):
        self.prompts = []
        self.confidence = 0.25
        self.configure_calls = []

    def configure_search(self, text_prompts=None, reference_image=None,
                         confidence=None):
        self.configure_calls.append(
            {"text_prompts": text_prompts, "confidence": confidence}
        )
        self.prompts = list(text_prompts or self.LABELS)
        return None

    def class_name(self, class_id):
        return self.prompts[class_id]

    def detect(self, frame):
        out = []

        for label, color in self.LABELS.items():
            if label not in self.prompts:
                continue

            mask = cv2.inRange(frame, np.clip(np.array(color) - 60, 0, 255), np.clip(np.array(color) + 60, 0, 255))
            ys, xs = np.where(mask > 0)

            if len(xs) < 50:
                continue

            out.append({
                "class_id": self.prompts.index(label),
                "class_name": label,
                "confidence": 0.9 if label == "backpack" else 0.6,
                "bbox": [int(xs.min()), int(ys.min()),
                         int(xs.max()), int(ys.max())],
            })

        return out


class ColorExtractor:
    """Embedding = normalised mean BGR colour of the crop."""

    def __init__(self):
        self.calls = 0

    def extract(self, image):
        self.calls += 1

        if isinstance(image, str):
            from PIL import Image
            image = Image.open(image).convert("RGB")

        vec = np.asarray(image, dtype=np.float32).reshape(-1, 3).mean(axis=0)
        vec = vec + 1e-3
        return vec / np.linalg.norm(vec)


class NumpySimilarity:
    def cosine_similarity(self, a, b):
        a, b = np.asarray(a), np.asarray(b)
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


class IoUTracker:
    """Minimal tracker with the same interface as ObjectTracker."""

    def __init__(self):
        self.tracks = {}
        self.next_id = 1

    @staticmethod
    def _iou(a, b):
        x1, y1 = max(a[0], b[0]), max(a[1], b[1])
        x2, y2 = min(a[2], b[2]), min(a[3], b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter)
        return inter / union if union else 0

    def update(self, detections):
        out = []

        for det in detections:
            best, best_iou = None, 0.05

            for tid, (bbox, cid) in self.tracks.items():
                if cid != det["class_id"]:
                    continue
                iou = self._iou(bbox, det["bbox"])
                if iou > best_iou:
                    best, best_iou = tid, iou

            if best is None:
                best = self.next_id
                self.next_id += 1

            self.tracks[best] = (det["bbox"], det["class_id"])
            out.append({
                "track_id": best,
                "class_id": det["class_id"],
                "confidence": det["confidence"],
                "bbox": det["bbox"],
            })

        return out
