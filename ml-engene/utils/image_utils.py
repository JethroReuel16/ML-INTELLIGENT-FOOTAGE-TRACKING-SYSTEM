from PIL import Image


def crop_object(frame, bbox):
    """
    Crop a detected object from an OpenCV frame.

    bbox format:
    [x1, y1, x2, y2]
    """

    x1, y1, x2, y2 = bbox

    # OpenCV uses BGR.
    # PIL expects RGB.
    frame_rgb = frame[:, :, ::-1]

    image = Image.fromarray(frame_rgb)

    # Make sure coordinates are valid
    x1 = max(0, x1)
    y1 = max(0, y1)

    x2 = min(image.width, x2)
    y2 = min(image.height, y2)

    if x2 <= x1 or y2 <= y1:
        return None

    cropped = image.crop(
        (x1, y1, x2, y2)
    )

    return cropped