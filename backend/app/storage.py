import os

from app.config import BACKEND_DIR, settings

# Persistent storage root (STORAGE_DIR / VISIONTRACE_STORAGE_DIR).
STORAGE_DIR = settings.storage_dir

UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
RESULTS_DIR = os.path.join(STORAGE_DIR, "results")
DEBUG_CROPS_DIR = os.path.join(STORAGE_DIR, "debug_crops")

# Results written before STORAGE_DIR existed live next to the code.
LEGACY_RESULTS_DIR = os.path.join(BACKEND_DIR, "results")
LEGACY_UPLOADS_DIR = os.path.join(BACKEND_DIR, "uploads")

for directory in (STORAGE_DIR, UPLOADS_DIR, RESULTS_DIR, DEBUG_CROPS_DIR):
    os.makedirs(directory, exist_ok=True)


def _unique_real(*directories):
    seen = []
    for directory in directories:
        real = os.path.realpath(os.path.abspath(directory))
        if real not in seen:
            seen.append(real)
    return seen


ALLOWED_RESULTS_DIRS = _unique_real(RESULTS_DIR, LEGACY_RESULTS_DIR)
ALLOWED_UPLOADS_DIRS = _unique_real(UPLOADS_DIR, LEGACY_UPLOADS_DIR)


def resolve_inside(path, allowed_directories):
    """Return the real path if it lies inside one of the directories, else None."""
    if not path:
        return None
    try:
        resolved = os.path.realpath(os.path.abspath(os.path.expanduser(str(path))))
    except (TypeError, ValueError, OSError):
        return None

    for directory in allowed_directories:
        try:
            if os.path.commonpath([resolved, directory]) == directory:
                return resolved
        except ValueError:
            # Different drives on Windows.
            continue
    return None
