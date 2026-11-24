"""
ML Footage Tracking System - command-line search.

Runs one search directly against the ML engine (no API or database), which is
useful for checking a server's models and performance.

    python main.py --video clip.mp4 --reference backpack.jpg
    python main.py --video clip.mp4 --text "black backpack" --interval 10
    python main.py --video clip.mp4 --reference ref.jpg --text backpack --json

Configuration (detector, device, ...) comes from the environment; see
ml_config.py.
"""

import argparse
import json
import logging
import sys
import time

from detection.base import DetectorCapabilityError


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Search a video for an object.")
    parser.add_argument("--video", required=True, help="Video file to search.")
    parser.add_argument("--reference", help="Reference image of the object.")
    parser.add_argument("--text", help='Text description, e.g. "black backpack".')
    parser.add_argument("--interval", type=int, default=5, help="Analyse every Nth frame (default 5).")
    parser.add_argument("--confidence", type=float, default=0.25, help="Minimum detection confidence (default 0.25).")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum ranked candidates (default 10).")
    parser.add_argument("--results-dir", default="results", help="Where evidence images are written.")
    parser.add_argument("--json", action="store_true", help="Print the full result as JSON.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log every observation.")
    args = parser.parse_args(argv)

    if not args.reference and not args.text:
        parser.error("provide --reference, --text, or both")

    return args


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from pipeline.search_pipeline import VisionTracePipeline

    started = time.monotonic()
    pipeline = VisionTracePipeline(results_folder=args.results_dir)
    loaded = time.monotonic() - started

    try:
        report = pipeline.search(
            reference_image=args.reference,
            video_path=args.video,
            text_prompt=args.text,
            frame_interval=args.interval,
            min_detection_confidence=args.confidence,
            max_results=args.max_results,
        )
    except (DetectorCapabilityError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    search = report["search"]
    print(f"\nSearch {report['search_id']} ({search['search_mode']}, detector {search['detector']['active']})")
    print(f"Models loaded in {loaded:.1f}s; video analysed in {search['processing_seconds']:.1f}s "
          f"({search['frames_analyzed']} frames, {search['unique_tracks']} tracks)\n")

    if not report["matches"]:
        print("No candidates found.")
    for match in report["matches"]:
        score = match["similarity_score"] if match["similarity_score"] is not None else match["detection_confidence"]
        print(f"#{match['rank']:<3} {match['match_status']:<15} {match['class_name']:<14} "
              f"score {score:.3f}  at {match['timestamp']:7.2f}s  track {match['track_id']}")
        print(f"     evidence: {match['evidence_image']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
