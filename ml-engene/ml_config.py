"""
Central ML-engine configuration.

All values come from environment variables so the same code runs on a
CPU-only laptop and on a GPU server without edits (the backend already uses
the same convention, e.g. VISIONTRACE_STORAGE_DIR).

    DETECTOR_MODEL        yoloe | yolo11n          (default: yoloe)
    DETECTOR_DEVICE       cpu | cuda | cuda:0 | mps (default: cpu)
    DETECTOR_CONFIDENCE   0..1                      (default: 0.25)
    DETECTOR_IMGSZ        inference size in pixels  (default: 640)
    YOLOE_CHECKPOINT      yoloe-11s-seg.pt (default)
    LEGACY_CHECKPOINT     yolo11n.pt       (default)
    YOLOE_VISUAL_PROMPT   true|false  experimental visual prompting (default: false)
    DINO_MODEL            Hugging Face id  (default: facebook/dinov2-base)
    DINO_DEVICE           cpu | cuda ...   (default: DETECTOR_DEVICE)
    MODELS_DIR            folder holding YOLO/YOLOE weights and
                          mobileclip_blt.ts (default: current directory)
    DETECTOR_IMGSZ_HIGH   inference size for "small objects" searches
                          (default: 1280; ~3x slower than 640)
    DINO_BATCH_SIZE       crops per DINOv2 forward pass (default: 16)
    ML_SAVE_DEBUG_CROPS   true|false  write every observed crop to disk
                          for debugging (default: false; grows without bound)
"""

import os
from dataclasses import dataclass

# Initial target categories. They are only the *default prompt set* for
# YOLOE; any other text prompt can be supplied per search.
DEFAULT_CATEGORIES = (
    "backpack",
    "handbag",
    "suitcase",
    "mobile phone",
    "laptop",
    "car",
    "motorcycle",
    "person",
    "shoe",
    "watch",
)

# COCO classes used by the legacy YOLO11n detector (backpack, handbag, suitcase).
LEGACY_ALLOWED_CLASSES = (24, 26, 28)

MAX_TEXT_PROMPTS = 20


def _env(name, default):
    value = os.getenv(name)
    return default if value is None or value.strip() == "" else value.strip()


def _env_bool(name, default=False):
    return _env(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _env_float(name, default):
    try:
        return float(_env(name, default))
    except ValueError:
        return float(default)


def _env_int(name, default):
    try:
        return int(_env(name, default))
    except ValueError:
        return int(default)


@dataclass(frozen=True)
class DetectorConfig:
    model: str = "yoloe"
    device: str = "cpu"
    confidence: float = 0.25
    imgsz: int = 640
    yoloe_checkpoint: str = "yoloe-11s-seg.pt"
    legacy_checkpoint: str = "yolo11n.pt"
    use_visual_prompt: bool = False
    default_categories: tuple = DEFAULT_CATEGORIES

    @classmethod
    def from_env(cls):
        return cls(
            model=_env("DETECTOR_MODEL", "yoloe").lower(),
            device=_env("DETECTOR_DEVICE", "cpu"),
            confidence=_env_float("DETECTOR_CONFIDENCE", 0.25),
            imgsz=_env_int("DETECTOR_IMGSZ", 640),
            yoloe_checkpoint=_env("YOLOE_CHECKPOINT", "yoloe-11s-seg.pt"),
            legacy_checkpoint=_env("LEGACY_CHECKPOINT", "yolo11n.pt"),
            use_visual_prompt=_env_bool("YOLOE_VISUAL_PROMPT", False),
        )


def dino_settings(default_device="cpu"):
    return {
        "model_name": _env("DINO_MODEL", "facebook/dinov2-base"),
        "device": _env("DINO_DEVICE", default_device),
        "batch_size": max(1, _env_int("DINO_BATCH_SIZE", 16)),
    }


def high_detail_imgsz():
    """Detector input size used when a search asks for small-object detail."""
    return max(320, _env_int("DETECTOR_IMGSZ_HIGH", 1280))


def models_dir():
    """Directory for detector weights, or None to use the working directory."""
    value = _env("MODELS_DIR", "")
    return os.path.abspath(value) if value else None


def save_debug_crops():
    """Whether to write every observed crop to the debug folder."""
    return _env_bool("ML_SAVE_DEBUG_CROPS", False)


def parse_text_prompts(text):
    """Split a free-text prompt into a clean, de-duplicated list.

    "black backpack, silver laptop" -> ["black backpack", "silver laptop"]
    """
    if not text:
        return []

    parts = []
    for chunk in str(text).replace(";", ",").replace("\n", ",").split(","):
        cleaned = " ".join(chunk.split())
        if cleaned:
            parts.append(cleaned[:80])

    return list(dict.fromkeys(parts))[:MAX_TEXT_PROMPTS]
