"""Tests for the production fixes to the ML engine (decoding, batching,
evidence handling, tracker configuration, labels, IDs)."""

import os
from datetime import datetime

import numpy as np
import pytest
from PIL import Image

from pipeline.search_pipeline import VisionTracePipeline
from tests.fakes import (
    FRAMES, RED, ColorDetector, ColorExtractor, IoUTracker, NumpySimilarity,
    make_reference, make_video,
)
from utils.image_utils import crop_object
from video.processor import VideoProcessor


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    return make_video(str(tmp_path_factory.mktemp("v") / "clip.mp4"))


def build(tmp_path, **kwargs):
    options = dict(
        debug_folder=str(tmp_path / "debug"),
        results_folder=str(tmp_path / "results"),
        detector=ColorDetector(),
        tracker_factory=IoUTracker,
        extractor=ColorExtractor(),
        similarity=NumpySimilarity(),
    )
    options.update(kwargs)
    return VisionTracePipeline(**options)


# ------------------------------------------------------------- decoding


class CountingDetector:
    def __init__(self):
        self.frames = []

    def detect(self, frame):
        self.frames.append(frame.shape)
        return []


def test_only_analysed_frames_are_decoded(video, monkeypatch):
    reads, grabs = [], []
    processor = VideoProcessor(video)
    real = processor.capture

    class Spy:
        def read(self):
            reads.append(1)
            return real.read()

        def grab(self):
            grabs.append(1)
            return real.grab()

        def __getattr__(self, name):
            return getattr(real, name)

    processor.capture = Spy()
    detector = CountingDetector()
    yielded = [f["frame_number"] for f in processor.process_frames(detector, frame_interval=10)]

    assert yielded == list(range(0, FRAMES, 10))
    assert len(reads) == len(yielded) + 1  # +1: final read hitting end of stream
    assert len(grabs) == FRAMES - len(yielded)  # skipped frames are never decoded
    assert processor.frame_count >= FRAMES


def test_timestamps_follow_frame_numbers(video):
    processor = VideoProcessor(video)
    frames = list(processor.process_frames(CountingDetector(), frame_interval=5))
    fps = processor.fps
    assert all(f["timestamp"] == pytest.approx(f["frame_number"] / fps) for f in frames)


# ------------------------------------------------------------- crops


def test_crop_object_converts_bgr_to_rgb_and_clamps():
    frame = np.zeros((50, 80, 3), dtype=np.uint8)
    frame[10:20, 30:40] = (255, 0, 0)  # pure blue in BGR

    crop = crop_object(frame, [30, 10, 40, 20])
    assert crop.size == (10, 10)
    assert crop.getpixel((5, 5)) == (0, 0, 255)  # blue in RGB

    clamped = crop_object(frame, [-5, -5, 500, 500])
    assert clamped.size == (80, 50)
    assert crop_object(frame, [40, 20, 30, 10]) is None


# ------------------------------------------------------------- batching


class BatchColorExtractor(ColorExtractor):
    """ColorExtractor with a batch API, recording how it is called."""

    def __init__(self):
        super().__init__()
        self.batch_sizes = []

    def extract_batch(self, images):
        self.batch_sizes.append(len(images))
        return np.stack([ColorExtractor.extract(self, image) for image in images])


class BatchSimilarity(NumpySimilarity):
    def cosine_similarity_many(self, reference, embeddings):
        reference = np.asarray(reference)
        return [self.cosine_similarity(reference, e) for e in np.asarray(embeddings)]


def test_batched_scoring_matches_per_item_scoring(tmp_path, video):
    ref = make_reference(str(tmp_path / "red.png"), RED)

    single = build(tmp_path / "a").search(reference_image=ref, video_path=video, frame_interval=5)
    batch_extractor = BatchColorExtractor()
    batched = build(tmp_path / "b", extractor=batch_extractor, similarity=BatchSimilarity()).search(
        reference_image=ref, video_path=video, frame_interval=5
    )

    strip = lambda r: [(m["track_id"], m["ranking_score"], m["timestamp"]) for m in r["matches"]]
    assert strip(single) == strip(batched)
    # Both objects in a frame share one forward pass.
    assert max(batch_extractor.batch_sizes) == 2


# ------------------------------------------------------------- evidence / disk


def test_no_debug_crops_by_default_but_evidence_is_saved(tmp_path, video, monkeypatch):
    monkeypatch.delenv("ML_SAVE_DEBUG_CROPS", raising=False)
    ref = make_reference(str(tmp_path / "red.png"), RED)
    pipeline = build(tmp_path)

    result = pipeline.search(reference_image=ref, video_path=video, frame_interval=5)

    assert not os.path.exists(tmp_path / "debug") or not os.listdir(tmp_path / "debug")
    assert result["matches"]
    for match in result["matches"]:
        with Image.open(match["evidence_image"]) as image:
            assert image.format == "JPEG" and image.width > 0

    # The top match's evidence is the reddest crop (the red object).
    with Image.open(result["matches"][0]["evidence_image"]) as image:
        r, g, b = np.asarray(image.convert("RGB"), dtype=float).reshape(-1, 3).mean(axis=0)
    assert r > 150 and g < 80 and b < 80


def test_debug_crops_can_be_enabled(tmp_path, video, monkeypatch):
    monkeypatch.setenv("ML_SAVE_DEBUG_CROPS", "true")
    ref = make_reference(str(tmp_path / "red.png"), RED)
    build(tmp_path).search(reference_image=ref, video_path=video, frame_interval=10)
    assert os.listdir(tmp_path / "debug")


# ------------------------------------------------------------- tracker config


def test_tracker_receives_user_confidence_floor(tmp_path, video):
    seen = []

    def factory(activation_threshold=None):
        seen.append(activation_threshold)
        return IoUTracker()

    pipeline = build(tmp_path, tracker_factory=factory)
    pipeline.search(reference_image=make_reference(str(tmp_path / "r.png"), RED),
                    video_path=video, min_detection_confidence=0.1)
    assert seen[-1] == 0.1


# ------------------------------------------------------------- labels / ids


def test_weak_best_match_is_not_called_top_candidate():
    status = VisionTracePipeline._get_match_status
    assert status(rank=1, ranking_score=0.05) == "LOW SIMILARITY"
    assert status(rank=1, ranking_score=0.40) == "TOP CANDIDATE"
    assert status(rank=2, ranking_score=0.40) == "CANDIDATE"
    assert status(rank=2, ranking_score=0.01) == "LOW SIMILARITY"


def test_report_timestamps_are_timezone_aware_and_ids_unique(tmp_path, video):
    pipeline = build(tmp_path)
    ref = make_reference(str(tmp_path / "red.png"), RED)
    a = pipeline.search(reference_image=ref, video_path=video, frame_interval=20)
    b = pipeline.search(reference_image=ref, video_path=video, frame_interval=20)

    assert datetime.fromisoformat(a["created_at"]).tzinfo is not None
    assert a["search_id"] != b["search_id"]
    assert a["search"]["processing_seconds"] >= 0


# ------------------------------------------------------------- real models (opt-in)


@pytest.mark.skipif(os.getenv("ML_REAL_MODELS") != "1", reason="set ML_REAL_MODELS=1 to load DINOv2")
def test_real_dinov2_batch_equals_single():
    import torch
    from embedding.feature_extractor import DINOv2FeatureExtractor

    extractor = DINOv2FeatureExtractor(batch_size=4)
    rng = np.random.default_rng(0)
    images = [Image.fromarray(rng.integers(0, 255, (h, w, 3), dtype=np.uint8)) for h, w in
              ((60, 40), (120, 90), (33, 200), (224, 224), (80, 80))]

    batch = extractor.extract_batch(images)
    singles = torch.stack([extractor.extract(image) for image in images])

    assert batch.shape == (5, 768)
    assert torch.allclose(batch.norm(dim=-1), torch.ones(5), atol=1e-5)
    assert torch.allclose(batch, singles, atol=1e-4)


# ------------------------------------------------------------- model directory


def test_models_dir_resolves_weights_without_touching_global_settings(tmp_path, monkeypatch):
    from detection.factory import use_models_dir
    from ml_config import DetectorConfig

    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    settings_file = None
    try:
        from ultralytics.utils import SETTINGS

        settings_file = getattr(SETTINGS, "file", None)
        before = settings_file.read_text() if settings_file and settings_file.exists() else None
    except Exception:
        SETTINGS = None

    config = use_models_dir(DetectorConfig(yoloe_checkpoint="yoloe-11s-seg.pt", legacy_checkpoint="yolo11n.pt"))

    assert config.yoloe_checkpoint == str(tmp_path / "models" / "yoloe-11s-seg.pt")
    assert config.legacy_checkpoint == str(tmp_path / "models" / "yolo11n.pt")
    # Explicit paths are left alone.
    explicit = use_models_dir(DetectorConfig(yoloe_checkpoint=str(tmp_path / "x" / "custom-seg.pt")))
    assert explicit.yoloe_checkpoint == str(tmp_path / "x" / "custom-seg.pt")

    if SETTINGS is not None:
        assert SETTINGS["weights_dir"] == str(tmp_path / "models")  # asset lookups redirected
        if settings_file and before is not None:
            assert settings_file.read_text() == before  # global settings file untouched


def test_models_dir_unset_keeps_working_directory_behaviour(monkeypatch):
    from detection.factory import use_models_dir
    from ml_config import DetectorConfig

    monkeypatch.delenv("MODELS_DIR", raising=False)
    config = DetectorConfig()
    assert use_models_dir(config) is config


# ------------------------------------------------------------- high detail


def test_high_detail_raises_detector_size_for_one_search_only(tmp_path, video, monkeypatch):
    monkeypatch.setenv("DETECTOR_IMGSZ_HIGH", "1280")
    detector = ColorDetector()
    detector.imgsz = 640
    seen = []
    original_detect = detector.detect

    def spy(frame):
        seen.append(detector.imgsz)
        return original_detect(frame)

    detector.detect = spy
    pipeline = build(tmp_path, detector=detector)
    ref = make_reference(str(tmp_path / "red.png"), RED)

    high = pipeline.search(reference_image=ref, video_path=video, frame_interval=20, high_detail=True)
    assert set(seen) == {1280} and high["search"]["detection_size"] == 1280
    assert detector.imgsz == 640  # restored afterwards

    seen.clear()
    normal = pipeline.search(reference_image=ref, video_path=video, frame_interval=20)
    assert set(seen) == {640} and normal["search"]["detection_size"] == 640


def test_high_detail_size_is_restored_when_search_fails(tmp_path, video):
    detector = ColorDetector()
    detector.imgsz = 640

    def boom(frame):
        raise RuntimeError("detector crashed")

    detector.detect = boom
    pipeline = build(tmp_path, detector=detector)
    with pytest.raises(RuntimeError):
        pipeline.search(reference_image=make_reference(str(tmp_path / "r.png"), RED),
                        video_path=video, high_detail=True)
    assert detector.imgsz == 640
