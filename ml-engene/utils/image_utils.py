from PIL import Image


def crop_object(frame, bbox):
    """
    Crop a detected object from an OpenCV (BGR) frame and return an RGB PIL image.

    bbox format: [x1, y1, x2, y2]. Returns None for an empty box.
    """
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (int(v) for v in bbox)

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, x2)
    y2 = min(height, y2)

    if x2 <= x1 or y2 <= y1:
        return None

    # Slice first, then convert only the crop (not the whole 1080p frame).
    region = frame[y1:y2, x1:x2, ::-1]

    return Image.fromarray(region.copy())
