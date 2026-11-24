import logging

import cv2

logger = logging.getLogger(__name__)


class VideoReadError(ValueError):
    """The video cannot be opened or decoded (corrupt, truncated, unsupported codec)."""


class VideoProcessor:
    """Sequential frame reader that only decodes the frames it analyses."""

    def __init__(self, video_path):
        self.video_path = video_path
        self.capture = cv2.VideoCapture(video_path)

        if not self.capture.isOpened():
            raise VideoReadError(
                "The video could not be opened. It may be corrupt, incomplete "
                "or in an unsupported format."
            )

        fps = self.capture.get(cv2.CAP_PROP_FPS)
        # Some recordings report 0 or absurd values; fall back to stream time.
        self.fps = fps if fps and 0 < fps <= 240 else 0.0
        self.frame_count = max(0, int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0))
        self.reported_frame_count = self.frame_count
        self.frames_read = 0

    def get_video_info(self):
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = self.frame_count / self.fps if self.fps > 0 else 0

        return {
            "fps": self.fps,
            "frame_count": self.frame_count,
            "width": width,
            "height": height,
            "duration": duration,
        }

    def _timestamp(self, frame_number):
        if self.fps > 0:
            return frame_number / self.fps
        # Unknown FPS: use the container's own position.
        return max(0.0, (self.capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0) / 1000.0)

    def process_frames(self, detector, frame_interval=30):
        """
        Yield every Nth frame with its detections.

        Skipped frames are only grabbed (demuxed), never decoded to pixels,
        which is the dominant cost for high-resolution footage.
        """
        frame_number = 0

        try:
            while True:
                if frame_number % frame_interval == 0:
                    success, frame = self.capture.read()

                    if not success or frame is None:
                        break

                    yield {
                        "frame_number": frame_number,
                        "timestamp": self._timestamp(frame_number),
                        "frame": frame,
                        "detections": detector.detect(frame),
                    }
                else:
                    if not self.capture.grab():
                        break

                frame_number += 1
        finally:
            self.capture.release()

        self.frames_read = frame_number

        # Container metadata can under-report; keep the real count.
        if frame_number > self.frame_count:
            self.frame_count = frame_number

    @property
    def ended_early(self):
        """True when decoding stopped well before the container's frame count."""
        reported = self.reported_frame_count
        return reported > 0 and self.frames_read < reported * 0.9

    def close(self):
        if self.capture.isOpened():
            self.capture.release()
