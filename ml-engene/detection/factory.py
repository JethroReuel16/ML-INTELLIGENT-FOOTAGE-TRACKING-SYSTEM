"""Config-driven detector selection with an explicit, reported fallback."""

import logging
import os

from dataclasses import replace

from ml_config import DetectorConfig, models_dir

logger = logging.getLogger(__name__)


# Files Ultralytics fetches by bare name (YOLOE also needs its text encoder).
TEXT_ENCODER_FILE = "mobileclip_blt.ts"


def use_models_dir(config):
    """
    Point weight lookups at MODELS_DIR instead of the working directory.

    Bare checkpoint names become absolute paths, and Ultralytics' own asset
    lookup (used for the YOLOE text encoder) is redirected in memory only -
    the user's global Ultralytics settings file is not modified.
    """
    directory = models_dir()

    if not directory:
        return config

    os.makedirs(directory, exist_ok=True)

    try:
        from ultralytics.utils import SETTINGS

        dict.__setitem__(SETTINGS, "weights_dir", directory)
    except Exception:  # ultralytics missing or changed; checkpoints still resolve
        logger.debug("Could not redirect the Ultralytics weights directory.", exc_info=True)

    def resolve(name):
        return name if os.path.isabs(name) or os.sep in name or "/" in name else os.path.join(directory, name)

    for name in (config.yoloe_checkpoint, config.legacy_checkpoint, TEXT_ENCODER_FILE):
        if not os.path.isfile(resolve(name)):
            logger.warning(
                "%s not found in MODELS_DIR (%s); it will be downloaded on first use, "
                "which needs internet access and can take a long time.",
                name,
                directory,
            )

    return replace(
        config,
        yoloe_checkpoint=resolve(config.yoloe_checkpoint),
        legacy_checkpoint=resolve(config.legacy_checkpoint),
    )


def _build_yoloe(config):
    from detection.yoloe_detector import YOLOEDetector

    return YOLOEDetector(
        checkpoint=config.yoloe_checkpoint,
        device=config.device,
        confidence=config.confidence,
        imgsz=config.imgsz,
        default_categories=config.default_categories,
        use_visual_prompt=config.use_visual_prompt,
    )


def _build_legacy(config):
    from detection.yolo_detector import YOLODetector

    return YOLODetector(
        model_path=config.legacy_checkpoint,
        device=config.device,
        confidence=config.confidence,
        imgsz=config.imgsz,
    )


# Add a new detector (e.g. Grounding DINO) by registering a builder here.
DETECTOR_BUILDERS = {
    "yoloe": _build_yoloe,
    "yolo11n": _build_legacy,
    "yolo": _build_legacy,
    "legacy": _build_legacy,
}


def create_detector(config: DetectorConfig = None):
    """
    Returns (detector, status).

    status reports what was requested, what is actually running, and why a
    fallback happened, so the system never claims YOLOE is active when it
    is not.
    """
    config = use_models_dir(config or DetectorConfig.from_env())

    status = {
        "requested": config.model,
        "active": None,
        "checkpoint": None,
        "device": config.device,
        "fallback": False,
        "fallback_reason": None,
    }

    builder = DETECTOR_BUILDERS.get(config.model)

    if builder is None:
        status["fallback"] = True
        status["fallback_reason"] = (
            f"Detector '{config.model}' is not available "
            f"(known: {', '.join(sorted(DETECTOR_BUILDERS))})."
        )
        builder = _build_legacy

    try:
        detector = builder(config)

    except Exception as error:  # model/weights/dependency failure
        if builder is _build_legacy:
            raise

        status["fallback"] = True
        status["fallback_reason"] = f"{type(error).__name__}: {error}"
        logger.warning(
            "Detector '%s' failed to load (%s). Falling back to YOLO11n.",
            config.model,
            status["fallback_reason"],
        )
        detector = _build_legacy(config)

    status["active"] = detector.name
    status["checkpoint"] = detector.checkpoint

    logger.info(
        "Active detector: %s (%s) on %s%s",
        status["active"],
        status["checkpoint"],
        config.device,
        " [FALLBACK]" if status["fallback"] else "",
    )

    return detector, status
