# ML Footage Tracking System — ML Engine

The search pipeline used in-process by the backend:

```
video ─► detector (YOLOE open-vocabulary, or YOLO11n) ─► ByteTrack tracking
      ─► object crops ─► DINOv2 embeddings (batched) ─► cosine similarity
      ─► per-track aggregation ─► ranked matches + evidence images
```

| Mode | Input | Ranking |
| --- | --- | --- |
| `image` | reference image | DINOv2 similarity to the reference |
| `text` | description, e.g. "black backpack" | detection confidence (no similarity score) |
| `image_text` | both | text selects what to detect, the image ranks it |

Text search needs YOLOE. If YOLOE cannot load, the engine falls back to
YOLO11n and reports the fallback (and why) in every result.

## Layout

```
pipeline/search_pipeline.py   Orchestration, aggregation, evidence, result report
detection/                    BaseDetector, YOLOE + YOLO11n, config-driven factory
tracking/object_tracker.py    ByteTrack wrapper (supervision)
embedding/feature_extractor.py  DINOv2 CLS embeddings (batched)
matching/similarity.py        Cosine similarity
video/processor.py            Frame reader (decodes only analysed frames)
ml_config.py                  Environment-driven configuration
main.py                       Command-line search
tools/benchmark.py            Detector / retrieval benchmarks on your own data
tests/                        Fast tests with fake models
```

## Configuration

| Variable | Default | |
| --- | --- | --- |
| `DETECTOR_MODEL` | `yoloe` | `yoloe` or `yolo11n` |
| `DETECTOR_DEVICE` | `cpu` | `cpu`, `cuda`, `cuda:0`, `mps` |
| `DETECTOR_IMGSZ` | `640` | Inference size |
| `DETECTOR_IMGSZ_HIGH` | `1280` | Inference size for "Detect small objects" searches (~3× slower) |
| `YOLOE_CHECKPOINT` | `yoloe-11s-seg.pt` | Must be a `*-seg.pt` (prompt-free `-pf` models can't take prompts) |
| `DINO_MODEL` | `facebook/dinov2-base` | Hugging Face model id |
| `DINO_DEVICE` | = `DETECTOR_DEVICE` | |
| `DINO_BATCH_SIZE` | `16` | Crops per DINOv2 forward pass |
| `ML_SAVE_DEBUG_CROPS` | `false` | Write every observed crop to `debug_crops/` (debugging only — grows without bound) |
| `MODELS_DIR` | working directory | Folder for `yoloe-11s-seg.pt`, `yolo11n.pt`, `mobileclip_blt.ts` |

**Pre-download the models when deploying** (≈1.2 GB in total):

```bash
MODELS_DIR=/data/models python -m tools.download_models
```

Otherwise they download during the first search, which needs internet access
and can take a long time on a slow link. If YOLOE's files cannot be fetched,
the engine falls back to YOLO11n (backpack / handbag / suitcase only, no text
search) and reports the fallback in every result. The Docker entrypoint runs
the download step automatically.

## Command line

```bash
python main.py --video clip.mp4 --reference backpack.jpg
python main.py --video clip.mp4 --text "black backpack" --interval 10
python main.py --video clip.mp4 --reference ref.jpg --text backpack --json
```

## Tests

```bash
pytest                       # fast: fake detector, tracker and embeddings
ML_REAL_MODELS=1 pytest      # also checks real DINOv2 batching (downloads ~350 MB)
```

## Performance notes

- Cost scales with *analysed frames × objects per frame*. Raise the frame
  interval for long footage; 5 at 25–30 fps samples ~5–6 frames per second.
- A CUDA GPU (`DETECTOR_DEVICE=cuda`) is typically an order of magnitude
  faster than CPU for both detection and embedding.
- The first search after start-up also loads the models (tens of seconds).

## Known limitation

`supervision.ByteTrack` is deprecated and removed in supervision 0.31, so the
version is pinned to 0.30.x. Migrating to the standalone `trackers` package is
the long-term fix.
