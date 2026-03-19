"""
Main pipeline orchestrator.
Scrape -> Normalize -> Deduplicate/Merge -> Validate -> Compare -> Write ONLY if changed.
Backups only created when data actually changes. Redundant data is eliminated.
"""
import asyncio
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path

from scraper.collegedunia_scraper import CollegeduniaScraper
from scraper.careers360_scraper import Careers360Scraper
from scraper.normalizer import normalize_source_data
from scraper.deduplicator import deduplicate_and_merge, has_data_changed
from scraper.validator import validate_colleges, validate_careers, validate_exams, validate_scholarships
from db.schema import (
    upsert_colleges_batch, upsert_careers_batch,
    upsert_exams_batch, upsert_scholarships_batch,
    get_all_colleges, get_all_careers, get_all_exams, get_all_scholarships,
    is_table_empty,
)

logger = logging.getLogger("scraper.pipeline")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
BACKUP_DIR = DATA_DIR / "backups"
REPORTS_DIR = Path(__file__).resolve().parent / "run_reports"

MAX_BACKUPS = 2  # Keep only last 2 full backups (= 8 files max)


def load_existing_data() -> dict:
    """Load current data from PostgreSQL tables.
    Falls back to JSON files if DB tables are empty (pre-migration).
    """
    try:
        if not is_table_empty("colleges"):
            data = {
                "colleges": get_all_colleges(),
                "careers": get_all_careers(),
                "exams": get_all_exams(),
                "scholarships": get_all_scholarships(),
            }
            logger.info("Loaded existing data from PostgreSQL.")
            return data
    except Exception as e:
        logger.warning(f"Could not load from PostgreSQL, falling back to JSON: {e}")

    # Fallback: load from JSON files
    data = {"colleges": [], "careers": [], "exams": [], "scholarships": []}
    file_map = {
        "colleges": ("uttarakhand_colleges_db.json", "colleges"),
        "careers": ("career_paths.json", "careers"),
        "exams": ("entrance_exams.json", "exams"),
        "scholarships": ("scholarships.json", "scholarships"),
    }
    for key, (fname, json_key) in file_map.items():
        try:
            with open(DATA_DIR / fname, "r", encoding="utf-8") as f:
                data[key] = json.load(f).get(json_key, [])
        except Exception as e:
            logger.warning(f"Could not load {fname}: {e}")
    return data


def backup_data():
    """Backup current JSON files. Only called when data is about to change."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    files = [
        "uttarakhand_colleges_db.json", "career_paths.json",
        "entrance_exams.json", "scholarships.json",
    ]
    for fname in files:
        src = DATA_DIR / fname
        if src.exists():
            shutil.copy2(src, BACKUP_DIR / f"{ts}_{fname}")

    # Prune: keep only last N backup sets (each set = 4 files with same timestamp)
    all_backups = sorted(BACKUP_DIR.glob("*_*.json"), reverse=True)
    timestamps = list(dict.fromkeys(f.name.split("_")[0] + "_" + f.name.split("_")[1] for f in all_backups))
    for old_ts in timestamps[MAX_BACKUPS:]:
        for f in BACKUP_DIR.glob(f"{old_ts}_*"):
            f.unlink()
            logger.debug(f"Pruned old backup: {f.name}")

    logger.info(f"Backup created with timestamp {ts}")


def write_data(colleges, careers, exams, scholarships):
    """Write validated data to JSON files."""
    with open(DATA_DIR / "uttarakhand_colleges_db.json", "w", encoding="utf-8") as f:
        json.dump({"colleges": colleges}, f, indent=2, ensure_ascii=False)

    with open(DATA_DIR / "career_paths.json", "w", encoding="utf-8") as f:
        json.dump({"careers": careers}, f, indent=2, ensure_ascii=False)

    with open(DATA_DIR / "entrance_exams.json", "w", encoding="utf-8") as f:
        json.dump({"exams": exams}, f, indent=2, ensure_ascii=False)

    with open(DATA_DIR / "scholarships.json", "w", encoding="utf-8") as f:
        json.dump({"scholarships": scholarships}, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Wrote: {len(colleges)} colleges, {len(careers)} careers, "
        f"{len(exams)} exams, {len(scholarships)} scholarships"
    )


def generate_changelog(old_data: dict, new_data: dict) -> dict:
    """Compare old and new data, return a summary of changes."""
    changelog = {}
    for data_type, name_field in [
        ("colleges", "college_name"), ("careers", "career_name"),
        ("exams", "exam_name"), ("scholarships", "name"),
    ]:
        old_names = {r[name_field] for r in old_data.get(data_type, []) if r.get(name_field)}
        new_names = {r[name_field] for r in new_data.get(data_type, []) if r.get(name_field)}
        changelog[data_type] = {
            "old_count": len(old_names),
            "new_count": len(new_names),
            "added": sorted(new_names - old_names),
            "removed": sorted(old_names - new_names),
            "unchanged_count": len(old_names & new_names),
        }
    return changelog


def save_run_report(report: dict):
    """Save pipeline run report to disk."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"{ts}_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Keep only last 5 reports
    for old in sorted(REPORTS_DIR.glob("*_report.json"), reverse=True)[5:]:
        old.unlink()


def load_run_reports() -> list[dict]:
    """Load all saved run reports."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for path in sorted(REPORTS_DIR.glob("*_report.json"), reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                reports.append(json.load(f))
        except Exception:
            pass
    return reports


async def run_full_pipeline() -> dict:
    """
    Main entry point. Scrape all sources, merge, validate, write ONLY if changed.

    Key behaviors:
    - Existing curated data is ALWAYS preserved (never deleted)
    - New scraped data is MERGED into existing (adds new, enriches existing)
    - Backup only created when data actually changes
    - JSON files only rewritten when data actually changes
    - Vector store only re-ingested when data actually changes
    """
    logger.info("=" * 60)
    logger.info("Starting scraping pipeline")
    logger.info("=" * 60)
    run_start = datetime.now()

    # 1. Load existing data
    existing_data = load_existing_data()
    logger.info(
        f"Existing data: {len(existing_data['colleges'])} colleges, "
        f"{len(existing_data['careers'])} careers, "
        f"{len(existing_data['exams'])} exams, "
        f"{len(existing_data['scholarships'])} scholarships"
    )

    # 2. Run scrapers concurrently
    scrapers = [
        CollegeduniaScraper(),
        Careers360Scraper(),
    ]
    results = await asyncio.gather(
        *[s.run() for s in scrapers],
        return_exceptions=True,
    )

    # 3. Collect successful results
    source_data = {}
    scraper_stats = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Scraper failed: {result}")
            continue
        source_data[result["source"]] = result
        scraper_stats[result["source"]] = result.get("stats", {})

    if not source_data:
        logger.error("All scrapers failed. Keeping existing data unchanged.")
        report = {
            "status": "error",
            "message": "All scrapers failed — existing data preserved",
            "started_at": run_start.isoformat(),
            "completed_at": datetime.now().isoformat(),
        }
        save_run_report(report)
        return report

    logger.info(f"Successful sources: {list(source_data.keys())}")

    # 4. Normalize
    normalized = {name: normalize_source_data(data) for name, data in source_data.items()}

    # 5. Deduplicate and merge with existing
    merged = deduplicate_and_merge(normalized, existing_data)

    # 6. Validate
    new_data = {
        "colleges": validate_colleges(merged["colleges"]),
        "careers": validate_careers(merged["careers"]),
        "exams": validate_exams(merged["exams"]),
        "scholarships": validate_scholarships(merged["scholarships"]),
    }

    # 7. Safety check — don't allow massive data loss
    old_count = len(existing_data.get("colleges", []))
    new_count = len(new_data["colleges"])
    if old_count > 0 and new_count < old_count * 0.5:
        logger.warning(f"Safety abort: colleges {old_count} -> {new_count}. Keeping existing.")
        report = {
            "status": "aborted",
            "message": f"Data drop detected ({old_count} -> {new_count} colleges)",
            "started_at": run_start.isoformat(),
            "completed_at": datetime.now().isoformat(),
        }
        save_run_report(report)
        return report

    # 8. Check if data actually changed
    changelog = generate_changelog(existing_data, new_data)
    data_changed = has_data_changed(existing_data, new_data)

    if not data_changed:
        logger.info("No data changes detected. Skipping write and re-ingestion.")
        duration = (datetime.now() - run_start).total_seconds()
        report = {
            "status": "no_changes",
            "message": "Scrape completed but no new data found — files unchanged",
            "started_at": run_start.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "duration_seconds": round(duration, 1),
            "sources_scraped": list(source_data.keys()),
            "scraper_stats": scraper_stats,
            "totals": {k: len(v) for k, v in new_data.items()},
        }
        save_run_report(report)
        return report

    # 9. Data changed — write to PostgreSQL + backup JSON
    logger.info("Data changes detected. Writing to PostgreSQL and backing up JSON.")
    backup_data()

    # Write to PostgreSQL (primary store)
    upsert_colleges_batch(new_data["colleges"])
    upsert_careers_batch(new_data["careers"])
    upsert_exams_batch(new_data["exams"])
    upsert_scholarships_batch(new_data["scholarships"])
    logger.info("PostgreSQL tables updated.")

    # Also update JSON files as backup/export
    write_data(new_data["colleges"], new_data["careers"], new_data["exams"], new_data["scholarships"])

    # 10. Re-ingest into vector store
    logger.info("Re-ingesting data into vector store...")
    try:
        from rag.ingest import ingest_all_data
        ingest_all_data()
        logger.info("Vector store re-ingestion complete")
    except Exception as e:
        logger.error(f"Vector store re-ingestion failed: {e}")

    # 11. Report
    duration = (datetime.now() - run_start).total_seconds()
    report = {
        "status": "success",
        "message": "Data updated successfully",
        "started_at": run_start.isoformat(),
        "completed_at": datetime.now().isoformat(),
        "duration_seconds": round(duration, 1),
        "sources_scraped": list(source_data.keys()),
        "scraper_stats": scraper_stats,
        "changelog": changelog,
        "totals": {k: len(v) for k, v in new_data.items()},
    }
    save_run_report(report)

    logger.info(f"Pipeline complete in {duration:.1f}s")
    logger.info(f"Changes: {changelog}")
    return report


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    result = asyncio.run(run_full_pipeline())
    print(json.dumps(result, indent=2))
