"""
Detector + retrieval benchmark for the ML Footage Tracking System.

Run it on YOUR machine with your own labelled data. It never invents numbers:
every figure is measured from the files you point it at.

1) Detector benchmark (per-frame latency, memory, precision/recall @ IoU 0.5)

   python -m tools.benchmark detect --images .\\bench\\images ^
       --annotations .\\bench\\annotations.json --detectors yolo11n yoloe

   annotations.json:
   { "img1.jpg": [ {"label": "backpack", "bbox": [x1, y1, x2, y2]} ] }

   Labels must use the prompt wording (backpack, handbag, suitcase,
   "mobile phone", laptop, car, motorcycle, person, shoe, watch). The legacy
   detector can only be scored on backpack / handbag / suitcase.

2) Retrieval benchmark (Precision@K, MRR, end-to-end time)

   python -m tools.benchmark retrieve --manifest .\\bench\\retrieval.json ^
       --detectors yolo11n yoloe --k 1 3 5

   retrieval.json:
   [ { "reference": "ref_backpack.jpg", "video": "cam1.mp4",
       "text_prompt": null, "relevant_windows": [[12.0, 18.5]] } ]
"""

import argparse
import json
import os
import sys
import time
from dataclasses import replace

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from ml_config import DEFAULT_CATEGORIES, DetectorConfig  # noqa: E402
from tools.metrics import (  # noqa: E402
    match_detections, precision_at_k, precision_recall, reciprocal_rank,
)

COCO_TO_PROMPT = {"backpack": "backpack", "handbag": "handbag", "suitcase": "suitcase"}


def peak_rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1e6
    except ImportError:
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except ImportError:
            return float("nan")


def build_detector(name, base):
    from detection.factory import create_detector
    detector, status = create_detector(replace(base, model=name))
    if status["fallback"]:
        raise SystemExit(
            f"'{name}' did not load ({status['fallback_reason']}). "
            "Refusing to benchmark a fallback under the wrong name."
        )
    return detector


def run_detect(args, base):
    import cv2

    with open(args.annotations, encoding="utf-8") as handle:
        annotations = json.load(handle)

    report = {}

    for name in args.detectors:
        rss_before = peak_rss_mb()
        detector = build_detector(name, base)
        detector.configure_search(
            list(DEFAULT_CATEGORIES) if detector.supports_text_prompts else None,
            confidence=args.confidence,
        )
        load_mb = peak_rss_mb() - rss_before

        times, counts = [], {}

        for filename, truth in annotations.items():
            frame = cv2.imread(os.path.join(args.images, filename))
            if frame is None:
                continue

            start = time.perf_counter()
            detections = detector.detect(frame)
            times.append(time.perf_counter() - start)

            for label in {t["label"] for t in truth} | {d["class_name"] for d in detections}:
                if name == "yolo11n" and label not in COCO_TO_PROMPT:
                    continue
                preds = [d for d in detections if d["class_name"] == label]
                truths = [t for t in truth if t["label"] == label]
                tp, fp, fn = match_detections(preds, truths)
                c = counts.setdefault(label, [0, 0, 0])
                c[0] += tp; c[1] += fp; c[2] += fn

        per_class = {}
        for label, (tp, fp, fn) in sorted(counts.items()):
            p, r = precision_recall(tp, fp, fn)
            per_class[label] = {"tp": tp, "fp": fp, "fn": fn,
                                "precision": round(p, 3), "recall": round(r, 3)}

        times_sorted = sorted(times)
        report[name] = {
            "images": len(times),
            "mean_ms": round(1000 * sum(times) / max(len(times), 1), 1),
            "p95_ms": round(1000 * times_sorted[int(0.95 * (len(times_sorted) - 1))], 1) if times else None,
            "model_load_rss_mb": round(load_mb, 1),
            "peak_rss_mb": round(peak_rss_mb(), 1),
            "per_class": per_class,
        }

    print(json.dumps(report, indent=2))


def run_retrieve(args, base):
    from pipeline.search_pipeline import VisionTracePipeline

    with open(args.manifest, encoding="utf-8") as handle:
        manifest = json.load(handle)

    report = {}

    for name in args.detectors:
        pipeline = VisionTracePipeline(
            debug_folder=os.path.join(args.workdir, "debug"),
            results_folder=os.path.join(args.workdir, "results"),
            config=replace(base, model=name),
        )
        if pipeline.detector_status["fallback"]:
            raise SystemExit(f"'{name}' fell back: {pipeline.detector_status['fallback_reason']}")

        rows = []
        for item in manifest:
            start = time.perf_counter()
            result = pipeline.search(
                reference_image=item.get("reference"),
                video_path=item["video"],
                text_prompt=item.get("text_prompt"),
                frame_interval=args.frame_interval,
                max_results=max(args.k),
            )
            elapsed = time.perf_counter() - start
            windows = item["relevant_windows"]
            rows.append({
                "video": item["video"],
                "seconds": round(elapsed, 1),
                "rr": reciprocal_rank(result["matches"], windows),
                **{f"p@{k}": precision_at_k(result["matches"], windows, k) for k in args.k},
            })

        n = max(len(rows), 1)
        report[name] = {
            "queries": len(rows),
            "MRR": round(sum(r["rr"] for r in rows) / n, 3),
            **{f"mean_P@{k}": round(sum(r[f"p@{k}"] for r in rows) / n, 3) for k in args.k},
            "mean_seconds": round(sum(r["seconds"] for r in rows) / n, 1),
            "peak_rss_mb": round(peak_rss_mb(), 1),
            "rows": rows,
        }

    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("detect")
    d.add_argument("--images", required=True)
    d.add_argument("--annotations", required=True)
    d.add_argument("--detectors", nargs="+", default=["yolo11n", "yoloe"])
    d.add_argument("--confidence", type=float, default=0.25)

    r = sub.add_parser("retrieve")
    r.add_argument("--manifest", required=True)
    r.add_argument("--detectors", nargs="+", default=["yolo11n", "yoloe"])
    r.add_argument("--k", nargs="+", type=int, default=[1, 3, 5])
    r.add_argument("--frame-interval", type=int, default=5)
    r.add_argument("--workdir", default="benchmark_output")

    args = parser.parse_args()
    base = DetectorConfig.from_env()

    if args.command == "detect":
        run_detect(args, base)
    else:
        run_retrieve(args, base)


if __name__ == "__main__":
    main()
