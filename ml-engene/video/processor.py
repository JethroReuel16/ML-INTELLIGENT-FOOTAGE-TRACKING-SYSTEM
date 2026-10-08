import cv2


class VideoProcessor:
    def __init__(self, video_path):
        self.video_path = video_path
        self.capture = cv2.VideoCapture(video_path)

        if not self.capture.isOpened():
            raise ValueError(
                f"Unable to open video: {video_path}"
            )

        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.frame_count = self.capture.get(
            cv2.CAP_PROP_FRAME_COUNT
        )

    def get_video_info(self):
        width = int(
            self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        )

        height = int(
            self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

        duration = (
            self.frame_count / self.fps
            if self.fps > 0
            else 0
        )

        return {
            "fps": self.fps,
            "frame_count": int(self.frame_count),
            "width": width,
            "height": height,
            "duration": duration,
        }

    def process_frames(
        self,
        detector,
        frame_interval=30,
    ):
        frame_number = 0

        while True:
            success, frame = self.capture.read()

            if not success:
                break

            if frame_number % frame_interval == 0:

                timestamp = (
                    frame_number / self.fps
                    if self.fps > 0
                    else 0
                )

                detections = detector.detect(frame)

                yield {
                    "frame_number": frame_number,
                    "timestamp": timestamp,
                    "frame": frame,
                    "detections": detections,
                }

            frame_number += 1

        self.capture.release()

    def close(self):
        if self.capture.isOpened():
            self.capture.release()