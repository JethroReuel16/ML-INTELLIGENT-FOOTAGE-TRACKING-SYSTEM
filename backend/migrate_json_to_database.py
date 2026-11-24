
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    User,
    VideoSource,
    SearchRecord,
    SearchMatch,
    MultiSourceSearch,
    MultiSourceItem,
    EvidenceFile,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"

SOURCES_FILE = DATA_DIR / "video_sources.json"

stats = {
    "sources": 0,
    "searches": 0,
    "matches": 0,
    "evidence": 0,
    "multi_searches": 0,
    "multi_items": 0,
    "skipped": 0,
    "errors": 0,
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read {path}: {error}")
        stats["errors"] += 1
        return None


def parse_datetime(value):
    if not value:
        return None

    try:
        if isinstance(value, datetime):
            return value

        value = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def parse_int(value):
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def parse_float(value):
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def valid_owner_id(db, value):
    """Return an existing numeric user ID, otherwise None."""
    owner_id = parse_int(value)

    if owner_id is None:
        return None

    user = db.query(User.id).filter(User.id == owner_id).first()
    return owner_id if user else None


def import_sources(db):
    print("\nIMPORTING VIDEO SOURCES...")

    if not SOURCES_FILE.exists():
        print("No video_sources.json file found. Skipping sources.")
        return

    sources = read_json(SOURCES_FILE)

    if not isinstance(sources, list):
        print("Video sources JSON is not a list. Skipping.")
        return

    for item in sources:
        try:
            source_id = item.get("id")

            if not source_id:
                stats["skipped"] += 1
                continue

            existing = db.get(VideoSource, source_id)

            if existing:
                stats["skipped"] += 1
                continue

            source = VideoSource(
                id=source_id,
                owner_id=valid_owner_id(db, item.get("owner_id")),
                name=item.get("name") or "Unnamed source",
                source_type=item.get("source_type") or "local",
                url=item.get("url") or "",
                location=item.get("location"),
                description=item.get("description"),
                last_connection_status=(
                    item.get("last_connection_status") or "not_tested"
                ),
                created_at=parse_datetime(item.get("created_at")),
                updated_at=parse_datetime(item.get("updated_at")),
                last_tested_at=parse_datetime(item.get("last_tested_at")),
            )

            db.add(source)
            db.flush()
            stats["sources"] += 1

        except Exception as error:
            db.rollback()
            print(f"Source import error: {error}")
            stats["errors"] += 1

    db.commit()
    print(f"Video sources imported: {stats['sources']}")


def import_searches(db):
    print("\nIMPORTING SEARCH RECORDS...")

    if not RESULTS_DIR.exists():
        print("Results directory not found.")
        return

    result_files = [
        path
        for path in RESULTS_DIR.rglob("result.json")
        if "multi_searches" not in path.parts
    ]

    for result_file in result_files:
        try:
            result = read_json(result_file)

            if not isinstance(result, dict):
                stats["skipped"] += 1
                continue

            search_id = result.get("search_id") or result_file.parent.name

            if db.get(SearchRecord, search_id):
                stats["skipped"] += 1
                continue

            summary_file = result_file.parent / "summary.json"
            summary = read_json(summary_file) if summary_file.exists() else None

            if not isinstance(summary, dict):
                summary = None

            video = result.get("video") or {}
            reference = result.get("reference") or {}
            search_settings = result.get("search") or {}

            record = SearchRecord(
                id=search_id,
                owner_id=valid_owner_id(db, result.get("owner_id")),
                status=result.get("status") or "unknown",
                created_at=parse_datetime(result.get("created_at")),
                reference_data=reference,
                video_metadata=video,
                search_settings=search_settings,
                video_path=video.get("path"),
                reference_image_path=reference.get("image"),
                duration=parse_float(video.get("duration")),
                fps=parse_float(video.get("fps")),
                frame_count=parse_int(video.get("frame_count")),
                result_payload=result,
                summary_payload=summary,
            )

            db.add(record)
            db.flush()

            stats["searches"] += 1

            matches = result.get("matches") or []

            for match_data in matches:
                if not isinstance(match_data, dict):
                    continue

                match = SearchMatch(
                    search_id=search_id,
                    rank=parse_int(match_data.get("rank")),
                    track_id=parse_int(match_data.get("track_id")),
                    class_id=parse_int(match_data.get("class_id")),
                    class_name=match_data.get("class_name"),
                    match_status=match_data.get("match_status"),
                    similarity_score=parse_float(
                        match_data.get("similarity_score")
                    ),
                    ranking_score=parse_float(
                        match_data.get("ranking_score")
                    ),
                    top3_average=parse_float(
                        match_data.get("top3_average")
                    ),
                    average_similarity=parse_float(
                        match_data.get("average_similarity")
                    ),
                    timestamp=parse_float(match_data.get("timestamp")),
                    frame_number=parse_int(match_data.get("frame_number")),
                    bbox=match_data.get("bbox"),
                    detection_confidence=parse_float(
                        match_data.get("detection_confidence")
                    ),
                    frames_observed=parse_int(
                        match_data.get("frames_observed")
                    ),
                    evidence_image=match_data.get("evidence_image"),
                    original_payload=match_data,
                )

                db.add(match)
                db.flush()

                stats["matches"] += 1

                evidence_path = match_data.get("evidence_image")

                if evidence_path:
                    evidence = EvidenceFile(
                        search_id=search_id,
                        match_id=match.id,
                        file_path=str(evidence_path),
                        file_type="image",
                    )
                    db.add(evidence)
                    stats["evidence"] += 1

            db.commit()
            print(f"Imported search: {search_id}")

        except Exception as error:
            db.rollback()
            print(f"Search import error in {result_file}: {error}")
            stats["errors"] += 1

    print(f"Search records imported: {stats['searches']}")
    print(f"Matches imported: {stats['matches']}")
    print(f"Evidence references imported: {stats['evidence']}")


def import_multi_source_searches(db):
    print("\nIMPORTING MULTI-SOURCE SEARCHES...")

    possible_directories = [
        RESULTS_DIR / "multi_searches",
        RESULTS_DIR / "multi_source_searches",
    ]

    manifest_files = []

    for directory in possible_directories:
        if directory.exists():
            manifest_files.extend(directory.glob("*.json"))

    for manifest_file in manifest_files:
        try:
            manifest = read_json(manifest_file)

            if not isinstance(manifest, dict):
                stats["skipped"] += 1
                continue

            multi_id = (
                manifest.get("multi_search_id")
                or manifest_file.stem
            )

            if db.get(MultiSourceSearch, multi_id):
                stats["skipped"] += 1
                continue

            source_items = manifest.get("sources") or []

            multi_record = MultiSourceSearch(
                id=multi_id,
                owner_id=valid_owner_id(db, manifest.get("owner_id")),
                status=manifest.get("status") or "unknown",
                created_at=parse_datetime(manifest.get("created_at")),
                source_count=parse_int(
                    manifest.get("source_count")
                ) or 0,
                successful_sources=parse_int(
                    manifest.get("successful_sources")
                ) or 0,
                failed_sources=parse_int(
                    manifest.get("failed_sources")
                ) or 0,
                settings=manifest.get("settings"),
                matches_payload=manifest.get("matches"),
                original_payload=manifest,
            )

            db.add(multi_record)
            db.flush()

            stats["multi_searches"] += 1

            for item in source_items:
                if not isinstance(item, dict):
                    continue

                source_id = item.get("source_id")
                search_id = item.get("search_id")

                # Only create foreign-key links when the referenced
                # records actually exist in PostgreSQL.
                if source_id and not db.get(VideoSource, source_id):
                    source_id = None

                if search_id and not db.get(SearchRecord, search_id):
                    search_id = None

                child = MultiSourceItem(
                    multi_search_id=multi_id,
                    source_id=source_id,
                    search_id=search_id,
                    source_name=item.get("source_name"),
                    source_type=item.get("source_type"),
                    status=item.get("status"),
                    match_count=parse_int(item.get("match_count")) or 0,
                    message=item.get("message"),
                    original_payload=item,
                )

                db.add(child)
                stats["multi_items"] += 1

            db.commit()
            print(f"Imported multi-source search: {multi_id}")

        except Exception as error:
            db.rollback()
            print(f"Multi-source import error in {manifest_file}: {error}")
            stats["errors"] += 1

    print(f"Multi-source searches imported: {stats['multi_searches']}")
    print(f"Multi-source items imported: {stats['multi_items']}")


def main():
    print("=" * 60)
    print("VISIONTRACE JSON TO POSTGRESQL MIGRATION")
    print("=" * 60)

    db: Session = SessionLocal()

    try:
        import_sources(db)
        import_searches(db)
        import_multi_source_searches(db)

        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)

        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")

        print("\nMigration process completed.")
        print("Original JSON files have NOT been deleted.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
