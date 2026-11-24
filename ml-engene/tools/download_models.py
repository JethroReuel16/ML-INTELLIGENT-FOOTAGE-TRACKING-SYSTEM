"""
Pre-download every model file the engine needs, so the first search does not
stall on (or silently fall back after) a slow download.

    MODELS_DIR=/data/models python -m tools.download_models

Fetches into MODELS_DIR (default: current directory):
  - the YOLOE checkpoint and its text encoder (mobileclip_blt.ts)
  - the legacy YOLO11n checkpoint (fallback detector)
and DINOv2 into the Hugging Face cache (HF_HOME).

Exits non-zero if anything could not be downloaded.
"""

import os
import shutil
import sys

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from ml_config import DetectorConfig, dino_settings, models_dir  # noqa: E402

TEXT_ENCODER_FILE = "mobileclip_blt.ts"


def fetch_ultralytics_asset(name, directory):
    from ultralytics.utils.downloads import attempt_download_asset

    target = os.path.join(directory, os.path.basename(name))
    if os.path.isfile(target):
        print(f"  ok      {target} (already present)")
        return True

    cwd = os.getcwd()
    try:
        os.chdir(directory)  # Ultralytics downloads bare names into the CWD
        path = attempt_download_asset(os.path.basename(name))
    finally:
        os.chdir(cwd)

    path = path if os.path.isabs(path) else os.path.join(directory, path)
    if os.path.isfile(path) and os.path.abspath(path) != os.path.abspath(target):
        shutil.move(path, target)

    ok = os.path.isfile(target)
    print(f"  {'ok' if ok else 'FAILED':7s} {target}")
    return ok


def fetch_dino():
    from transformers import AutoImageProcessor, AutoModel

    name = dino_settings()["model_name"]
    AutoImageProcessor.from_pretrained(name)
    AutoModel.from_pretrained(name)
    print(f"  ok      {name} (Hugging Face cache: {os.getenv('HF_HOME', '~/.cache/huggingface')})")
    return True


def main():
    directory = models_dir() or os.getcwd()
    os.makedirs(directory, exist_ok=True)
    config = DetectorConfig.from_env()

    print(f"Downloading models into {directory}")
    results = []
    for name in (config.yoloe_checkpoint, TEXT_ENCODER_FILE, config.legacy_checkpoint):
        try:
            results.append(fetch_ultralytics_asset(name, directory))
        except Exception as error:  # network, permissions, unknown asset
            print(f"  FAILED  {name}: {type(error).__name__}: {error}")
            results.append(False)

    try:
        results.append(fetch_dino())
    except Exception as error:
        print(f"  FAILED  DINOv2: {type(error).__name__}: {error}")
        results.append(False)

    if not all(results):
        print("\nSome models could not be downloaded; see above.")
        return 1

    print("\nAll models are available.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
