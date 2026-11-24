"""Pure metric helpers used by benchmark.py (unit-tested)."""


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union > 0 else 0.0


def match_detections(predictions, truths, iou_threshold=0.5):
    """Greedy one-to-one matching for ONE image and ONE category.

    predictions: [{"bbox", "confidence"}]   truths: [{"bbox"}]
    Returns (tp, fp, fn).
    """
    unmatched = list(range(len(truths)))
    tp = 0

    for pred in sorted(predictions, key=lambda p: -p["confidence"]):
        best, best_iou = None, iou_threshold

        for i in unmatched:
            value = iou(pred["bbox"], truths[i]["bbox"])
            if value >= best_iou:
                best, best_iou = i, value

        if best is not None:
            unmatched.remove(best)
            tp += 1

    return tp, len(predictions) - tp, len(unmatched)


def precision_recall(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return precision, recall


def precision_at_k(matches, relevant_windows, k, slack=1.0):
    """Retrieval Precision@K.

    matches: ranked list of dicts with a "timestamp" (seconds).
    relevant_windows: [[start_s, end_s], ...] where the target is visible.
    A match is relevant when its timestamp falls inside a window (+/- slack).
    """
    top = matches[:k]

    if not top:
        return 0.0

    hits = sum(
        1 for m in top
        if any(start - slack <= m["timestamp"] <= end + slack
               for start, end in relevant_windows)
    )

    return hits / len(top)


def reciprocal_rank(matches, relevant_windows, slack=1.0):
    for rank, m in enumerate(matches, start=1):
        if any(start - slack <= m["timestamp"] <= end + slack
               for start, end in relevant_windows):
            return 1.0 / rank

    return 0.0
