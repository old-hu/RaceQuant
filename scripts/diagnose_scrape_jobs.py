from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("data/processed/hkjc_structured.sqlite")
DEFAULT_OUTPUT = Path("data/reports/scrape_job_diagnostics_latest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose official historical scrape job health.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--mark-unmatched-skipped",
        action="store_true",
        help="Mark pending/failed jobs with no matching official_race_days row as skipped_no_official_result.",
    )
    args = parser.parse_args()

    report = build_report(args.db, mark_unmatched_skipped=args.mark_unmatched_skipped)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(console_summary(report), ensure_ascii=False, indent=2))


def build_report(db_path: Path, mark_unmatched_skipped: bool = False) -> dict[str, Any]:
    con = sqlite3.connect(db_path, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        unmatched_before = rows(con, UNMATCHED_ACTIVE_SQL)
        marked = 0
        if mark_unmatched_skipped and unmatched_before:
            marked = mark_unmatched(con)
            con.commit()

        report = {
            "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "dbPath": str(db_path),
            "markedUnmatchedSkipped": marked,
            "statusCounts": rows(con, "SELECT status, COUNT(*) AS count FROM scrape_jobs GROUP BY status ORDER BY status"),
            "activeByYear": rows(con, ACTIVE_BY_YEAR_SQL),
            "activeByRacecourse": rows(con, ACTIVE_BY_RACECOURSE_SQL),
            "oldestPending": rows(con, OLD_PENDING_SQL),
            "runningJobs": rows(con, RUNNING_SQL),
            "failedJobs": rows(con, FAILED_SQL),
            "doneWithWarningsJobs": rows(con, DONE_WITH_WARNINGS_SQL),
            "failureReasons": rows(con, FAILURE_REASONS_SQL),
            "unmatchedActiveJobs": rows(con, UNMATCHED_ACTIVE_SQL),
        }
    finally:
        con.close()
    return report


UNMATCHED_ACTIVE_SQL = """
SELECT sj.id, sj.race_date AS raceDate, sj.racecourse, sj.status, sj.attempts, sj.last_error AS lastError
FROM scrape_jobs sj
LEFT JOIN official_race_days ord
    ON ord.race_date = sj.race_date
    AND ord.racecourse = sj.racecourse
WHERE sj.status IN ('pending', 'failed')
  AND ord.race_date IS NULL
ORDER BY sj.race_date, sj.racecourse
LIMIT 500
"""

ACTIVE_BY_YEAR_SQL = """
SELECT substr(race_date, 1, 4) AS year, status, COUNT(*) AS count
FROM scrape_jobs
WHERE status IN ('pending', 'running', 'failed')
GROUP BY year, status
ORDER BY year, status
"""

ACTIVE_BY_RACECOURSE_SQL = """
SELECT racecourse, status, COUNT(*) AS count
FROM scrape_jobs
WHERE status IN ('pending', 'running', 'failed')
GROUP BY racecourse, status
ORDER BY racecourse, status
"""

OLD_PENDING_SQL = """
SELECT id, race_date AS raceDate, racecourse, status, attempts, created_at AS createdAt, updated_at AS updatedAt
FROM scrape_jobs
WHERE status = 'pending'
ORDER BY race_date, racecourse
LIMIT 50
"""

RUNNING_SQL = """
SELECT id, race_date AS raceDate, racecourse, status, attempts, started_at AS startedAt, updated_at AS updatedAt
FROM scrape_jobs
WHERE status = 'running'
ORDER BY started_at, race_date, racecourse
"""

FAILED_SQL = """
SELECT id, race_date AS raceDate, racecourse, attempts, last_error AS lastError, updated_at AS updatedAt
FROM scrape_jobs
WHERE status = 'failed'
ORDER BY updated_at DESC, race_date DESC
LIMIT 100
"""

DONE_WITH_WARNINGS_SQL = """
SELECT id, race_date AS raceDate, racecourse, attempts, last_error AS lastError, updated_at AS updatedAt
FROM scrape_jobs
WHERE status = 'done_with_warnings'
ORDER BY updated_at DESC, race_date DESC
LIMIT 100
"""

FAILURE_REASONS_SQL = """
SELECT COALESCE(NULLIF(last_error, ''), '<empty>') AS reason, COUNT(*) AS count
FROM scrape_jobs
WHERE status = 'failed'
GROUP BY reason
ORDER BY count DESC, reason
LIMIT 50
"""


def mark_unmatched(con: sqlite3.Connection) -> int:
    before = con.total_changes
    con.execute(
        """
        UPDATE scrape_jobs
        SET status = 'skipped_no_official_result',
            finished_at = COALESCE(finished_at, datetime('now')),
            updated_at = datetime('now'),
            last_error = COALESCE(NULLIF(last_error, ''), 'No matching official race day discovered')
        WHERE id IN (
            SELECT sj.id
            FROM scrape_jobs sj
            LEFT JOIN official_race_days ord
                ON ord.race_date = sj.race_date
                AND ord.racecourse = sj.racecourse
            WHERE sj.status IN ('pending', 'failed')
              AND ord.race_date IS NULL
        )
        """
    )
    return con.total_changes - before


def rows(con: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in con.execute(sql).fetchall()]


def console_summary(report: dict[str, Any]) -> dict[str, Any]:
    active = sum(item["count"] for item in report["statusCounts"] if item["status"] in {"pending", "running", "failed"})
    return {
        "activeJobs": active,
        "statusCounts": report["statusCounts"],
        "markedUnmatchedSkipped": report["markedUnmatchedSkipped"],
        "unmatchedActiveJobs": len(report["unmatchedActiveJobs"]),
        "runningJobs": report["runningJobs"],
        "failedJobs": len(report["failedJobs"]),
        "doneWithWarningsJobs": len(report["doneWithWarningsJobs"]),
    }


if __name__ == "__main__":
    main()
