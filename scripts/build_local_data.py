from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_RAW_DIR = ROOT_DIR / "data" / "raw" / "hkjc"
DEFAULT_EXPORTS_DIR = ROOT_DIR / "frontend" / "public" / "data"
DEFAULT_STRUCTURED_DB = ROOT_DIR / "data" / "processed" / "hkjc_structured.sqlite"
DEFAULT_ODDS_DB = ROOT_DIR / "data" / "processed" / "legacy_horse_odds.sqlite"
DEFAULT_REPORT = ROOT_DIR / "data" / "reports" / "local_data_build.json"

sys.path.insert(0, str(SCRIPT_DIR))

from audit_legacy_odds import audit_legacy_odds  # noqa: E402
from audit_structured_data import build_report as build_structured_audit  # noqa: E402
from ensure_odds_indexes import INDEX_SQL as ODDS_INDEX_SQL  # noqa: E402
from hkjc_structured_store import connect, parse_change_outputs, parse_horse_history_outputs, parse_job_outputs  # noqa: E402
from hkjc_structured_store import set_raw_dir  # noqa: E402
from rebuild_local_sqlite_from_exports import rebuild_odds_db, rebuild_structured_db, reset_sqlite_database  # noqa: E402


SourceMode = Literal["raw", "json-cache", "auto"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build local research SQLite databases from the canonical local data pipeline."
    )
    parser.add_argument("--source", choices=["raw", "json-cache", "auto"], default="raw")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--exports-dir", type=Path, default=DEFAULT_EXPORTS_DIR)
    parser.add_argument("--structured-db", type=Path, default=DEFAULT_STRUCTURED_DB)
    parser.add_argument("--odds-db", type=Path, default=DEFAULT_ODDS_DB)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--max-race-no", type=int, default=12)
    parser.add_argument(
        "--scrape-once",
        action="store_true",
        help="Run one pending historical scrape job before building from raw data.",
    )
    args = parser.parse_args()

    structured_db = args.structured_db.resolve()
    odds_db = args.odds_db.resolve()
    if args.reset:
        for path in (structured_db, odds_db):
            reset_sqlite_database(path)

    selected_source = choose_source(args.source, args.raw_dir, args.exports_dir)
    if args.scrape_once:
        run_scrape_once(structured_db, args.raw_dir.resolve(), args.max_race_no)
        selected_source = "raw"
    if selected_source == "raw":
        structured_counts = build_structured_from_raw(structured_db, args.raw_dir.resolve(), args.max_race_no)
        odds_counts = ensure_existing_odds_db(odds_db)
    else:
        structured_counts = rebuild_structured_db(args.exports_dir.resolve(), structured_db)
        odds_counts = rebuild_odds_db(args.exports_dir.resolve(), odds_db)

    report = build_report(
        source=selected_source,
        raw_dir=args.raw_dir.resolve(),
        exports_dir=args.exports_dir.resolve(),
        structured_db=structured_db,
        odds_db=odds_db,
        structured_counts=structured_counts,
        odds_counts=odds_counts,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(console_summary(report), ensure_ascii=False, indent=2))
    print(f"Wrote local data build report to {args.report}")


def choose_source(requested: SourceMode, raw_dir: Path, exports_dir: Path) -> Literal["raw", "json-cache"]:
    if requested == "raw":
        return "raw"
    if requested == "json-cache":
        return "json-cache"
    return "raw" if has_raw_cache(raw_dir) else "json-cache"


def has_raw_cache(raw_dir: Path) -> bool:
    return raw_dir.exists() and any(raw_dir.glob("*/*/latest.json"))


def build_structured_from_raw(db_path: Path, raw_dir: Path, max_race_no: int) -> dict[str, int]:
    set_raw_dir(raw_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as con:
        jobs = con.execute(
            """
            SELECT DISTINCT race_date, racecourse
            FROM scrape_jobs
            ORDER BY race_date, racecourse
            """
        ).fetchall()

    parsed_counts: dict[str, int] = {}
    for job in jobs:
        merge_counts(
            parsed_counts,
            parse_job_outputs(job["race_date"], job["racecourse"], max_race_no=max_race_no, db_path=db_path),
        )
    merge_counts(parsed_counts, parse_change_outputs(db_path=db_path))
    merge_counts(parsed_counts, parse_horse_history_outputs(db_path=db_path))

    with connect(db_path) as con:
        table_counts = count_existing_tables(
            con,
            [
                "race_metadata",
                "race_results",
                "race_entries",
                "dividends",
                "race_change_events",
                "horse_profiles",
                "horse_form_records",
                "scrape_jobs",
                "model_predictions",
            ],
        )
    return {"parsed": parsed_counts, "tables": table_counts}


def run_scrape_once(db_path: Path, raw_dir: Path, max_race_no: int) -> None:
    from run_historical_scrape_worker import run_next_job

    run_next_job(max_race_no=max_race_no, report_dir=ROOT_DIR / "data" / "reports", db_path=db_path, raw_dir=raw_dir)


def ensure_existing_odds_db(db_path: Path) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        return {"legacy_horse_odds": 0}
    con = sqlite3.connect(db_path)
    try:
        if not table_exists(con, "legacy_horse_odds"):
            return {"legacy_horse_odds": 0}
        for sql in ODDS_INDEX_SQL:
            con.execute(sql)
        con.commit()
        return count_existing_tables(con, ["legacy_horse_odds"])
    finally:
        con.close()


def build_report(
    source: str,
    raw_dir: Path,
    exports_dir: Path,
    structured_db: Path,
    odds_db: Path,
    structured_counts: dict[str, Any],
    odds_counts: dict[str, int],
) -> dict[str, Any]:
    structured_audit = build_structured_audit(structured_db) if structured_db.exists() else None
    odds_audit = audit_legacy_odds(odds_db) if odds_db.exists() else {"exists": False, "snapshotCount": 0}
    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": source,
        "sourceMeaning": source_meaning(source),
        "rawDir": str(raw_dir),
        "exportsDir": str(exports_dir),
        "structuredDb": str(structured_db),
        "oddsDb": str(odds_db),
        "structuredCounts": structured_counts,
        "oddsCounts": odds_counts,
        "structuredAudit": structured_audit,
        "oddsAudit": odds_audit,
    }


def source_meaning(source: str) -> str:
    if source == "raw":
        return "Canonical local build from parsed HKJC raw scrape outputs and existing odds database."
    return "Bootstrap build from frontend/public/data JSON cache; use only when raw/local databases are unavailable."


def console_summary(report: dict[str, Any]) -> dict[str, Any]:
    structured_audit = report.get("structuredAudit") or {}
    odds_audit = report.get("oddsAudit") or {}
    return {
        "source": report["source"],
        "structuredCounts": report["structuredCounts"],
        "oddsCounts": report["oddsCounts"],
        "structuredDateRange": structured_audit.get("date_range"),
        "structuredIssues": structured_audit.get("issue_counts"),
        "oddsSnapshotCount": odds_audit.get("snapshotCount"),
        "oddsDuplicateGroups": odds_audit.get("duplicateGroupCount"),
        "oddsMissingTypes": odds_audit.get("missingOddsTypes"),
        "oddsCriticalMissing": odds_audit.get("criticalMissing"),
        "oddsAnomalies": odds_audit.get("anomalyCounts"),
    }


def merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + int(value)


def count_existing_tables(con: sqlite3.Connection, table_names: list[str]) -> dict[str, int]:
    return {
        table_name: int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
        for table_name in table_names
        if table_exists(con, table_name)
    }


def table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


if __name__ == "__main__":
    main()
