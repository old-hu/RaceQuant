from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("data/processed/hkjc_structured.sqlite")
DEFAULT_OUTPUT = Path("data/reports/data_readiness_latest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a detailed official-data readiness report for RaceQuant.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = build_report(args.db)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(console_summary(report), ensure_ascii=False, indent=2))


def build_report(db_path: Path) -> dict[str, Any]:
    con = sqlite3.connect(db_path, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        job_status = rows(
            con,
            """
            SELECT status, COUNT(*) AS count
            FROM scrape_jobs
            GROUP BY status
            ORDER BY status
            """,
        )
        active_jobs = scalar(con, "SELECT COUNT(*) FROM scrape_jobs WHERE status IN ('pending', 'running', 'failed')")
        official_days = scalar(con, "SELECT COUNT(*) FROM official_race_days")
        completed_days = scalar(con, "SELECT COUNT(*) FROM scrape_jobs WHERE status IN ('done', 'done_with_warnings')")

        coverage_by_year = rows(con, COVERAGE_BY_YEAR_SQL)
        coverage_by_racecourse = rows(con, COVERAGE_BY_RACECOURSE_SQL)
        recent_missing_components = rows(con, RECENT_MISSING_COMPONENTS_SQL)
        horse_history = dict(
            con.execute(
                """
                SELECT
                    COUNT(*) AS profiles,
                    SUM(CASE WHEN horse_code IS NULL OR horse_code = '' THEN 1 ELSE 0 END) AS profiles_missing_code
                FROM horse_profiles
                """
            ).fetchone()
        )
        horse_history["form_records"] = scalar(con, "SELECT COUNT(*) FROM horse_form_records")
        horse_history["horses_with_form"] = scalar(
            con,
            "SELECT COUNT(DISTINCT horse_code) FROM horse_form_records WHERE horse_code IS NOT NULL AND horse_code <> ''",
        )
        result_range = dict_or_none(
            con.execute(
                """
                SELECT
                    MIN(race_date) AS min_date,
                    MAX(race_date) AS max_date,
                    COUNT(DISTINCT race_date) AS dates,
                    COUNT(DISTINCT race_date || '|' || racecourse || '|' || race_no) AS races,
                    COUNT(*) AS runners
                FROM race_results
                """
            ).fetchone()
        )
        critical_missing = rows(con, CRITICAL_MISSING_SQL)
    finally:
        con.close()

    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "dbPath": str(db_path),
        "readyForTraining": active_jobs == 0,
        "officialBackfill": {
            "officialRaceDays": official_days,
            "completedJobs": completed_days,
            "activeJobs": active_jobs,
            "jobStatus": job_status,
            "completionRate": ratio(completed_days, official_days),
        },
        "resultRange": result_range,
        "horseHistory": horse_history,
        "coverageByYear": coverage_by_year,
        "coverageByRacecourse": coverage_by_racecourse,
        "recentMissingComponents": recent_missing_components,
        "criticalMissing": critical_missing,
    }


COVERAGE_BY_YEAR_SQL = """
WITH official AS (
    SELECT substr(race_date, 1, 4) AS year, COUNT(*) AS official_days
    FROM official_race_days
    GROUP BY year
),
jobs AS (
    SELECT substr(race_date, 1, 4) AS year, status, COUNT(*) AS count
    FROM scrape_jobs
    GROUP BY year, status
),
metadata AS (
    SELECT substr(race_date, 1, 4) AS year, COUNT(DISTINCT race_date || '|' || racecourse || '|' || race_no) AS races
    FROM race_metadata
    GROUP BY year
),
entries AS (
    SELECT substr(race_date, 1, 4) AS year, COUNT(*) AS runners
    FROM race_entries
    WHERE standby = 0
    GROUP BY year
),
results AS (
    SELECT substr(race_date, 1, 4) AS year, COUNT(DISTINCT race_date || '|' || racecourse || '|' || race_no) AS races, COUNT(*) AS runners
    FROM race_results
    GROUP BY year
),
dividend_counts AS (
    SELECT substr(race_date, 1, 4) AS year, COUNT(*) AS rows
    FROM dividends
    GROUP BY year
)
SELECT
    official.year,
    official.official_days AS officialDays,
    COALESCE(SUM(CASE WHEN jobs.status IN ('done', 'done_with_warnings') THEN jobs.count END), 0) AS doneJobs,
    COALESCE(SUM(CASE WHEN jobs.status = 'done_with_warnings' THEN jobs.count END), 0) AS doneWithWarningsJobs,
    COALESCE(SUM(CASE WHEN jobs.status IN ('pending', 'running', 'failed') THEN jobs.count END), 0) AS activeJobs,
    COALESCE(SUM(CASE WHEN jobs.status = 'skipped_no_official_result' THEN jobs.count END), 0) AS skippedJobs,
    COALESCE(metadata.races, 0) AS metadataRaces,
    COALESCE(entries.runners, 0) AS entryRunners,
    COALESCE(results.races, 0) AS resultRaces,
    COALESCE(results.runners, 0) AS resultRunners,
    COALESCE(dividend_counts.rows, 0) AS dividendRows
FROM official
LEFT JOIN jobs ON jobs.year = official.year
LEFT JOIN metadata ON metadata.year = official.year
LEFT JOIN entries ON entries.year = official.year
LEFT JOIN results ON results.year = official.year
LEFT JOIN dividend_counts ON dividend_counts.year = official.year
GROUP BY official.year
ORDER BY official.year
"""

COVERAGE_BY_RACECOURSE_SQL = """
WITH official AS (
    SELECT racecourse, COUNT(*) AS official_days
    FROM official_race_days
    GROUP BY racecourse
),
jobs AS (
    SELECT racecourse, status, COUNT(*) AS count
    FROM scrape_jobs
    GROUP BY racecourse, status
),
results AS (
    SELECT racecourse, COUNT(DISTINCT race_date || '|' || racecourse || '|' || race_no) AS races, COUNT(*) AS runners
    FROM race_results
    GROUP BY racecourse
)
SELECT
    official.racecourse,
    official.official_days AS officialDays,
    COALESCE(SUM(CASE WHEN jobs.status IN ('done', 'done_with_warnings') THEN jobs.count END), 0) AS doneJobs,
    COALESCE(SUM(CASE WHEN jobs.status = 'done_with_warnings' THEN jobs.count END), 0) AS doneWithWarningsJobs,
    COALESCE(SUM(CASE WHEN jobs.status IN ('pending', 'running', 'failed') THEN jobs.count END), 0) AS activeJobs,
    COALESCE(results.races, 0) AS resultRaces,
    COALESCE(results.runners, 0) AS resultRunners
FROM official
LEFT JOIN jobs ON jobs.racecourse = official.racecourse
LEFT JOIN results ON results.racecourse = official.racecourse
GROUP BY official.racecourse
ORDER BY official.racecourse
"""

RECENT_MISSING_COMPONENTS_SQL = """
SELECT
    sj.race_date AS raceDate,
    sj.racecourse,
    sj.status,
    CASE WHEN EXISTS (SELECT 1 FROM race_metadata rm WHERE rm.race_date = sj.race_date AND rm.racecourse = sj.racecourse) THEN 0 ELSE 1 END AS missingMetadata,
    CASE WHEN EXISTS (SELECT 1 FROM race_entries re WHERE re.race_date = sj.race_date AND re.racecourse = sj.racecourse) THEN 0 ELSE 1 END AS missingEntries,
    CASE WHEN EXISTS (SELECT 1 FROM race_results rr WHERE rr.race_date = sj.race_date AND rr.racecourse = sj.racecourse) THEN 0 ELSE 1 END AS missingResults,
    CASE WHEN EXISTS (SELECT 1 FROM dividends d WHERE d.race_date = sj.race_date AND d.racecourse = sj.racecourse) THEN 0 ELSE 1 END AS missingDividends
FROM scrape_jobs sj
WHERE sj.status IN ('done', 'done_with_warnings')
  AND (
      NOT EXISTS (SELECT 1 FROM race_metadata rm WHERE rm.race_date = sj.race_date AND rm.racecourse = sj.racecourse)
      OR NOT EXISTS (SELECT 1 FROM race_entries re WHERE re.race_date = sj.race_date AND re.racecourse = sj.racecourse)
      OR NOT EXISTS (SELECT 1 FROM race_results rr WHERE rr.race_date = sj.race_date AND rr.racecourse = sj.racecourse)
      OR NOT EXISTS (SELECT 1 FROM dividends d WHERE d.race_date = sj.race_date AND d.racecourse = sj.racecourse)
  )
ORDER BY sj.race_date DESC, sj.racecourse
LIMIT 200
"""

CRITICAL_MISSING_SQL = """
SELECT 'race_metadata.distance_m' AS field, COUNT(*) AS count FROM race_metadata WHERE distance_m IS NULL
UNION ALL SELECT 'race_metadata.race_class', COUNT(*) FROM race_metadata WHERE race_class IS NULL OR race_class = ''
UNION ALL SELECT 'race_results.horse_code', COUNT(*) FROM race_results WHERE horse_code IS NULL OR horse_code = ''
UNION ALL SELECT 'race_results.draw', COUNT(*) FROM race_results WHERE draw IS NULL OR draw = ''
UNION ALL SELECT 'race_results.actual_weight', COUNT(*) FROM race_results WHERE actual_weight IS NULL OR actual_weight = ''
UNION ALL SELECT 'race_results.declared_horse_weight', COUNT(*) FROM race_results WHERE declared_horse_weight IS NULL OR declared_horse_weight = ''
UNION ALL SELECT 'race_results.jockey', COUNT(*) FROM race_results WHERE jockey IS NULL OR jockey = ''
UNION ALL SELECT 'race_results.trainer', COUNT(*) FROM race_results WHERE trainer IS NULL OR trainer = ''
"""


def scalar(con: sqlite3.Connection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0] or 0)


def rows(con: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in con.execute(sql).fetchall()]


def dict_or_none(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def console_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "readyForTraining": report["readyForTraining"],
        "officialBackfill": report["officialBackfill"],
        "resultRange": report["resultRange"],
        "horseHistory": report["horseHistory"],
        "recentMissingComponents": len(report["recentMissingComponents"]),
    }


if __name__ == "__main__":
    main()
