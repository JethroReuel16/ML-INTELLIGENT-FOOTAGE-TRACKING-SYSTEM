import os
import sys
import types

import numpy as np
import pytest

from detection.base import DetectorCapabilityError
from detection.factory import create_detector
from ml_config import DetectorConfig
from pipeline.search_pipeline import (
    VisionTracePipeline, resolve_search_mode,
)
from tests.fakes import (
    RED, ColorDetector, ColorExtractor, IoUTracker, NumpySimilarity,
    install_fake_ultralytics, make_reference, make_video,
)


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    return make_video(str(tmp_path_factory.mktemp("v") / "clip.mp4"))


@pytest.fixture
def pipeline(tmp_path):
    extractor = ColorExtractor()
    p = VisionTracePipeline(
        debug_folder=str(tmp_path / "debug"),
        results_folder=str(tmp_path / "results"),
        detector=ColorDetector(),
        tracker_factory=IoUTracker,
        extractor=extractor,
        similarity=NumpySimilarity(),
    )
    p.extractor_ref = extractor
    return p


@pytest.fixture
def red_ref(tmp_path):
    return make_reference(str(tmp_path / "red.png"), RED)


# ------------------------------------------------------------------ modes
def test_resolve_search_mode():
    assert resolve_search_mode("a.jpg", None) == "image"
    assert resolve_search_mode(None, "black backpack") == "text"
    assert resolve_search_mode("a.jpg", "black backpack") == "image_text"
    assert resolve_search_mode("a.jpg", None, "image") == "image"
    with pytest.raises(ValueError):
        resolve_search_mode(None, "  ")
    with pytest.raises(ValueError):
        resolve_search_mode("a.jpg", None, "text")
    with pytest.raises(ValueError):
        resolve_search_mode("a.jpg", None, "nonsense")


# ------------------------------------------------------------ image search
def test_image_search_ranks_matching_colour_first(pipeline, video, red_ref):
    report = pipeline.search(reference_image=red_ref, video_path=video,
                             frame_interval=3)
    assert report["search"]["search_mode"] == "image"
    assert report["search"]["ranking_basis"] == "dinov2_similarity"

    matches = report["matches"]
    assert len(matches) == 2                       # one track per object
    top, other = matches
    assert top["class_name"] == "backpack" and top["rank"] == 1
    assert top["match_status"] == "TOP CANDIDATE"
    assert top["similarity_score"] > other["similarity_score"]
    assert top["similarity_score"] > 0.99          # red crop vs red reference
    assert other["class_name"] == "laptop"         # visually different -> lower


def test_report_contains_all_contract_fields(pipeline, video, red_ref):
    m = pipeline.search(reference_image=red_ref, video_path=video,
                        frame_interval=3)["matches"][0]
    for key in ("rank", "track_id", "class_id", "class_name", "match_status",
                "similarity_score", "ranking_score", "top3_average",
                "average_similarity", "timestamp", "frame_number", "bbox",
                "detection_confidence", "frames_observed", "evidence_image"):
        assert key in m, key
    assert len(m["bbox"]) == 4
    assert os.path.isfile(m["evidence_image"])     # evidence saved
    assert m["frame_number"] % 3 == 0              # sampled frames only
    assert m["timestamp"] == pytest.approx(m["frame_number"] / 10, abs=1e-3)


def test_ranking_formula_is_unchanged(pipeline, video, red_ref):
    report = pipeline.search(reference_image=red_ref, video_path=video,
                             frame_interval=3)
    out = pipeline.search_video(
        video, pipeline.create_reference_embedding(red_ref), frame_interval=3)
    track = out["results"][0]
    scores = sorted((f["similarity"] for f in track["frames"]), reverse=True)
    expected = (0.50 * scores[0]
                + 0.30 * sum(scores[:3]) / len(scores[:3])
                + 0.20 * sum(scores) / len(scores))
    assert track["combined_score"] == pytest.approx(expected)
    assert report["matches"][0]["ranking_score"] == pytest.approx(expected, abs=1e-5)


def test_tracking_ids_stable_and_objects_enter_leave(pipeline, video, red_ref):
    pipeline.detector.configure_search()   # search() does this before search_video()
    out = pipeline.search_video(
        video, pipeline.create_reference_embedding(red_ref), frame_interval=3)
    tracks = {t["class_name"]: t for t in out["results"]}
    assert set(tracks) == {"backpack", "laptop"}
    assert tracks["backpack"]["track_id"] != tracks["laptop"]["track_id"]
    red_frames = [f["frame_number"] for f in tracks["backpack"]["frames"]]
    blue_frames = [f["frame_number"] for f in tracks["laptop"]["frames"]]
    assert min(red_frames) == 0 and max(red_frames) >= 84      # whole video
    assert min(blue_frames) >= 30                              # enters later
    assert len(red_frames) > len(blue_frames)


# ------------------------------------------------------------- text search
def test_text_search_uses_prompt_and_no_similarity(pipeline, video):
    pipeline.extractor_ref.calls = 0
    report = pipeline.search(video_path=video, text_prompt="laptop",
                             frame_interval=3)
    assert report["search"]["search_mode"] == "text"
    assert report["search"]["ranking_basis"] == "detection_confidence"
    assert report["search"]["prompts"] == ["laptop"]
    assert len(report["matches"]) == 1
    m = report["matches"][0]
    assert m["class_name"] == "laptop"
    assert m["similarity_score"] is None           # never faked
    assert m["average_similarity"] is None
    assert m["ranking_score"] == pytest.approx(0.6, abs=1e-3)   # confidence-based
    assert m["search_prompt"] == "laptop"
    assert pipeline.extractor_ref.calls == 0       # DINOv2 not used


def test_text_search_multiple_prompts(pipeline, video):
    report = pipeline.search(video_path=video, text_prompt="backpack, laptop",
                             frame_interval=3)
    assert {m["class_name"] for m in report["matches"]} == {"backpack", "laptop"}


def test_image_plus_text_restricts_detection_then_ranks_by_similarity(
        pipeline, video, red_ref):
    report = pipeline.search(reference_image=red_ref, video_path=video,
                             text_prompt="backpack", frame_interval=3)
    assert report["search"]["search_mode"] == "image_text"
    assert report["search"]["ranking_basis"] == "dinov2_similarity"
    assert [m["class_name"] for m in report["matches"]] == ["backpack"]
    assert report["matches"][0]["similarity_score"] > 0.99


def test_request_confidence_reaches_the_detector(pipeline, video, red_ref):
    pipeline.search(reference_image=red_ref, video_path=video,
                    min_detection_confidence=0.1, frame_interval=30)
    assert pipeline.detector.configure_calls[-1]["confidence"] == 0.1


def test_max_results_limits_output(pipeline, video, red_ref):
    report = pipeline.search(reference_image=red_ref, video_path=video,
                             frame_interval=3, max_results=1)
    assert len(report["matches"]) == 1


def test_validation_errors(pipeline, video, red_ref, tmp_path):
    with pytest.raises(ValueError):
        pipeline.search(video_path=video)                      # nothing supplied
    with pytest.raises(FileNotFoundError):
        pipeline.search(reference_image=red_ref,
                        video_path=str(tmp_path / "missing.mp4"))
    with pytest.raises(ValueError):
        pipeline.search_video(video, None, frame_interval=0)


# ---------------------------------------------- legacy detector / fallback
def test_legacy_pipeline_keeps_original_class_filter(tmp_path, video, red_ref):
    install_fake_ultralytics()
    detector, status = create_detector(DetectorConfig(model="yolo11n"))
    p = VisionTracePipeline(
        debug_folder=str(tmp_path / "d"), results_folder=str(tmp_path / "r"),
        detector=detector, detector_status=status, tracker_factory=IoUTracker,
        extractor=ColorExtractor(), similarity=NumpySimilarity())
    assert detector.configure_search() == {24, 26, 28}
    report = p.search(reference_image=red_ref, video_path=video, frame_interval=30)
    assert report["search"]["detector"]["active"] == "yolo11n"
    assert report["search"]["detector"]["fallback"] is False


def test_text_search_on_fallback_detector_gives_clear_error(tmp_path, video):
    install_fake_ultralytics(yoloe_fails=True)
    detector, status = create_detector(DetectorConfig(model="yoloe"))
    p = VisionTracePipeline(
        debug_folder=str(tmp_path / "d"), results_folder=str(tmp_path / "r"),
        detector=detector, detector_status=status, tracker_factory=IoUTracker,
        extractor=ColorExtractor(), similarity=NumpySimilarity())
    with pytest.raises(DetectorCapabilityError) as err:
        p.search(video_path=video, text_prompt="laptop")
    message = str(err.value)
    assert "yolo11n" in message and "weights could not be downloaded" in message


# ------------------------------------------------ ByteTrack adapter format
def test_object_tracker_adapter_with_stub_supervision(monkeypatch):
    class Dets:
        def __init__(self, xyxy, confidence, class_id, tracker_id=None):
            self.xyxy, self.confidence = xyxy, confidence
            self.class_id, self.tracker_id = class_id, tracker_id

    class ByteTrack:
        # Mirrors supervision's constructor (track_activation_threshold, ...).
        def __init__(self, track_activation_threshold=0.25, **kwargs):
            self.track_activation_threshold = track_activation_threshold

        def update_with_detections(self, d):
            return Dets(d.xyxy, d.confidence, d.class_id,
                        np.arange(1, len(d.xyxy) + 1))

    sv = types.ModuleType("supervision")
    sv.Detections, sv.ByteTrack = Dets, ByteTrack
    monkeypatch.setitem(sys.modules, "supervision", sv)
    monkeypatch.delitem(sys.modules, "tracking.object_tracker", raising=False)

    from tracking.object_tracker import ObjectTracker
    # The user's confidence floor reaches ByteTrack.
    assert ObjectTracker(activation_threshold=0.1).tracker.track_activation_threshold == 0.1
    out = ObjectTracker().update([
        {"class_id": 3, "class_name": "x", "confidence": 0.7, "bbox": [1, 2, 30, 40]}])
    assert out == [{"track_id": 1, "class_id": 3,
                    "confidence": pytest.approx(0.7), "bbox": [1, 2, 30, 40]}]
    assert ObjectTracker().update([]) == []
