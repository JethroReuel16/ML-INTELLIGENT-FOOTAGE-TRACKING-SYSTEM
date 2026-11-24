import pytest

from detection.base import DetectorCapabilityError
from detection.factory import create_detector
from ml_config import DetectorConfig, DEFAULT_CATEGORIES, parse_text_prompts
from tests.fakes import FakeYOLOE, install_fake_ultralytics


@pytest.fixture(autouse=True)
def fake_ultralytics():
    install_fake_ultralytics()


def cfg(**kw):
    return DetectorConfig(**kw)


def test_default_categories_are_the_ten_targets():
    assert set(DEFAULT_CATEGORIES) == {
        "backpack", "handbag", "suitcase", "mobile phone", "laptop",
        "car", "motorcycle", "person", "shoe", "watch",
    }


def test_parse_text_prompts():
    assert parse_text_prompts("Black backpack, silver laptop;  red motorcycle") == [
        "Black backpack", "silver laptop", "red motorcycle"]
    assert parse_text_prompts("  ") == []
    assert parse_text_prompts(None) == []
    assert parse_text_prompts("a, a, A") == ["a", "A"]  # de-duplicated, case kept
    assert len(parse_text_prompts(",".join(f"obj{i}" for i in range(50)))) == 20


def test_yoloe_applies_default_prompts_and_reports_active():
    detector, status = create_detector(cfg(model="yoloe"))
    assert status["active"] == "yoloe" and status["fallback"] is False
    assert FakeYOLOE.instances[-1].set_classes_calls == [list(DEFAULT_CATEGORIES)]


def test_yoloe_text_prompts_and_caching():
    detector, _ = create_detector(cfg(model="yoloe"))
    model = FakeYOLOE.instances[-1]

    detector.configure_search(["black backpack"], confidence=0.1)
    assert model.set_classes_calls[-1] == ["black backpack"]
    n = len(model.set_classes_calls)

    detector.configure_search(["black backpack"])        # same prompts
    assert len(model.set_classes_calls) == n             # text encoder not re-run

    out = detector.detect(frame=object())
    assert out[0]["class_name"] == "black backpack"
    assert out[0]["bbox"] == [10, 20, 110, 220]
    assert model.predict_calls[-1]["conf"] == 0.1        # request threshold honoured


def test_yoloe_bbox_confidence_class_format_for_bytetrack():
    detector, _ = create_detector(cfg(model="yoloe"))
    det = detector.detect(object())[0]
    assert set(det) == {"class_id", "class_name", "confidence", "bbox"}
    assert isinstance(det["class_id"], int) and isinstance(det["confidence"], float)
    assert all(isinstance(v, int) for v in det["bbox"])


def test_yoloe_visual_prompt_is_opt_in_and_restores_text_classes(tmp_path):
    from PIL import Image
    ref = tmp_path / "ref.jpg"
    Image.new("RGB", (80, 60)).save(ref)

    detector, _ = create_detector(cfg(model="yoloe", use_visual_prompt=True))
    model = FakeYOLOE.instances[-1]

    detector.configure_search(None, reference_image=str(ref))
    detector.detect(object())
    kwargs = model.predict_calls[-1]
    assert kwargs["refer_image"] == str(ref)
    assert kwargs["visual_prompts"]["bboxes"].tolist() == [[0.0, 0.0, 80.0, 60.0]]

    before = len(model.set_classes_calls)
    detector.configure_search(["laptop"])                # next search, text again
    assert len(model.set_classes_calls) == before + 1    # classes restored
    assert "refer_image" not in (detector.detect(object()) and model.predict_calls[-1])


def test_yoloe_visual_prompt_disabled_by_default(tmp_path):
    from PIL import Image
    ref = tmp_path / "ref.jpg"
    Image.new("RGB", (80, 60)).save(ref)
    detector, _ = create_detector(cfg(model="yoloe"))
    detector.configure_search(None, reference_image=str(ref))
    detector.detect(object())
    assert "refer_image" not in FakeYOLOE.instances[-1].predict_calls[-1]


def test_prompt_free_checkpoint_rejected():
    detector, status = create_detector(cfg(model="yoloe", yoloe_checkpoint="yoloe-11s-seg-pf.pt"))
    assert status["fallback"] is True and "Prompt-free" in status["fallback_reason"]


def test_legacy_detector_keeps_coco_classes_and_rejects_text():
    detector, status = create_detector(cfg(model="yolo11n"))
    assert status == {**status, "active": "yolo11n", "fallback": False}
    assert detector.configure_search() == {24, 26, 28}
    assert detector.detect(object())[0]["class_name"] == "backpack"
    with pytest.raises(DetectorCapabilityError):
        detector.configure_search(["laptop"])


def test_fallback_is_reported_not_silent():
    install_fake_ultralytics(yoloe_fails=True)
    detector, status = create_detector(cfg(model="yoloe"))
    assert detector.name == "yolo11n"
    assert status["requested"] == "yoloe" and status["active"] == "yolo11n"
    assert status["fallback"] is True
    assert "weights could not be downloaded" in status["fallback_reason"]


def test_unknown_detector_falls_back_with_reason():
    detector, status = create_detector(cfg(model="grounding_dino"))
    assert status["fallback"] is True and "not available" in status["fallback_reason"]


def test_confidence_override_applies_to_legacy_detector():
    detector, _ = create_detector(cfg(model="yolo11n"))
    detector.configure_search(confidence=0.4)
    detector.detect(object())
    assert detector.model.call_kwargs[-1]["conf"] == 0.4
