from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 HKJC 结构化数据完整性。")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--output", type=Path, default=Path("data/reports/structured_data_audit.json"))
    args = parser.parse_args()

    report = build_report(args.db)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary_for_console(report), ensure_ascii=False, indent=2))


def build_report(db_path: Path) -> dict[str, Any]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        result_races = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT race_date, racecourse, race_no
                FROM race_results
            )
            """,
        )
        result_runners = scalar(con, "SELECT COUNT(*) FROM race_results")
        metadata_races = scalar(con, "SELECT COUNT(*) FROM race_metadata")
        entry_runners = scalar(con, "SELECT COUNT(*) FROM race_entries WHERE standby = 0")

        missing_metadata = rows(
            con,
            """
            SELECT rr.race_date, rr.racecourse, rr.race_no, COUNT(*) AS runners
            FROM race_results rr
            LEFT JOIN race_metadata rm
                ON rm.race_date = rr.race_date
                AND rm.racecourse = rr.racecourse
                AND rm.race_no = rr.race_no
            WHERE rm.race_date IS NULL
            GROUP BY rr.race_date, rr.racecourse, rr.race_no
            ORDER BY rr.race_date DESC, rr.racecourse, rr.race_no
            """,
        )
        missing_entries = rows(
            con,
            """
            SELECT rr.race_date, rr.racecourse, rr.race_no, rr.horse_no, rr.horse_name, rr.horse_code
            FROM race_results rr
            LEFT JOIN race_entries re
                ON re.race_date = rr.race_date
                AND re.racecourse = rr.racecourse
                AND re.race_no = rr.race_no
                AND re.horse_no = rr.horse_no
                AND re.standby = 0
            WHERE re.race_date IS NULL
            ORDER BY rr.race_date DESC, rr.racecourse, rr.race_no, CAST(rr.horse_no AS INTEGER)
            """,
        )
        duplicate_runners = rows(
            con,
            """
            SELECT race_date, racecourse, race_no, horse_no, COUNT(*) AS count
            FROM race_results
            GROUP BY race_date, racecourse, race_no, horse_no
            HAVING COUNT(*) > 1
            ORDER BY count DESC, race_date DESC
            """,
        )
        critical_missing = {
            "race_metadata.distance_m": scalar(con, "SELECT COUNT(*) FROM race_metadata WHERE distance_m IS NULL"),
            "race_metadata.surface": scalar(con, "SELECT COUNT(*) FROM race_metadata WHERE surface IS NULL OR surface = ''"),
            "race_metadata.race_class": scalar(con, "SELECT COUNT(*) FROM race_metadata WHERE race_class IS NULL OR race_class = ''"),
            "race_results.horse_code": scalar(con, "SELECT COUNT(*) FROM race_results WHERE horse_code IS NULL OR horse_code = ''"),
            "race_results.draw": scalar(con, "SELECT COUNT(*) FROM race_results WHERE draw IS NULL OR draw = ''"),
            "race_results.actual_weight": scalar(con, "SELECT COUNT(*) FROM race_results WHERE actual_weight IS NULL OR actual_weight = ''"),
            "race_results.declared_horse_weight": scalar(
                con,
                "SELECT COUNT(*) FROM race_results WHERE declared_horse_weight IS NULL OR declared_horse_weight = ''",
            ),
            "race_results.jockey": scalar(con, "SELECT COUNT(*) FROM race_results WHERE jockey IS NULL OR jockey = ''"),
            "race_results.trainer": scalar(con, "SELECT COUNT(*) FROM race_results WHERE trainer IS NULL OR trainer = ''"),
        }
        date_range = dict_or_none(
            con.execute("SELECT MIN(race_date) AS min_date, MAX(race_date) AS max_date FROM race_results").fetchone()
        )
        job_status = rows(
            con,
            """
            SELECT status, COUNT(*) AS count
            FROM scrape_jobs
            GROUP BY status
            ORDER BY status
            """,
        )
    finally:
        con.close()

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "db_path": str(db_path),
        "counts": {
            "result_races": result_races,
            "result_runners": result_runners,
            "metadata_races": metadata_races,
            "entry_runners": entry_runners,
        },
        "date_range": date_range,
        "coverage": {
            "metadata_race_coverage": ratio(result_races - len(missing_metadata), result_races),
            "entry_runner_coverage": ratio(result_runners - len(missing_entries), result_runners),
        },
        "critical_missing": critical_missing,
        "issues": {
            "missing_metadata_races": missing_metadata[:200],
            "missing_entries": missing_entries[:200],
            "duplicate_result_runners": duplicate_runners[:200],
        },
        "issue_counts": {
            "missing_metadata_races": len(missing_metadata),
            "missing_entries": len(missing_entries),
            "duplicate_result_runners": len(duplicate_runners),
        },
        "scrape_jobs": job_status,
    }


def scalar(con: sqlite3.Connection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0] or 0)


def rows(con: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in con.execute(sql).fetchall()]


def dict_or_none(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def summary_for_console(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "counts": report["counts"],
        "date_range": report["date_range"],
        "coverage": report["coverage"],
        "issue_counts": report["issue_counts"],
        "critical_missing": report["critical_missing"],
    }


if __name__ == "__main__":
    main()
