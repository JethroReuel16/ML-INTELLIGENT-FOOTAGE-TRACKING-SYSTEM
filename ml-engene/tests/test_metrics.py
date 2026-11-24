import pytest

from tools.metrics import (
    iou, match_detections, precision_at_k, precision_recall, reciprocal_rank,
)


def test_iou():
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert iou([0, 0, 10, 10], [5, 0, 15, 10]) == pytest.approx(1 / 3)


def test_match_detections_counts():
    truths = [{"bbox": [0, 0, 10, 10]}, {"bbox": [50, 50, 60, 60]}]
    preds = [{"bbox": [0, 0, 10, 11], "confidence": 0.9},
             {"bbox": [100, 100, 120, 120], "confidence": 0.8}]
    assert match_detections(preds, truths) == (1, 1, 1)
    assert precision_recall(1, 1, 1) == (0.5, 0.5)
    assert precision_recall(0, 0, 0) == (0.0, 0.0)


def test_duplicate_predictions_do_not_double_count():
    truths = [{"bbox": [0, 0, 10, 10]}]
    preds = [{"bbox": [0, 0, 10, 10], "confidence": 0.9},
             {"bbox": [0, 0, 10, 10], "confidence": 0.8}]
    assert match_detections(preds, truths) == (1, 1, 0)


def test_precision_at_k_and_mrr():
    matches = [{"timestamp": 50}, {"timestamp": 12}, {"timestamp": 14}, {"timestamp": 90}]
    windows = [[10, 15]]
    assert precision_at_k(matches, windows, 1) == 0.0
    assert precision_at_k(matches, windows, 3) == pytest.approx(2 / 3)
    assert precision_at_k(matches, windows, 10) == 0.5     # only 4 returned
    assert precision_at_k([], windows, 3) == 0.0
    assert reciprocal_rank(matches, windows) == 0.5
    assert reciprocal_rank([{"timestamp": 99}], windows) == 0.0
