from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("data/processed/legacy_horse_odds.sqlite")
DEFAULT_REPORT = Path("data/reports/legacy_odds_audit.json")


def audit_legacy_odds(db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        if not table_exists(con, "legacy_horse_odds"):
            return {
                "dbPath": str(db_path),
                "tableExists": False,
                "snapshotCount": 0,
                "duplicateGroupCount": 0,
                "duplicateSnapshotCount": 0,
                "duplicateGroups": [],
            }

        snapshot_count = scalar(con, "SELECT COUNT(*) FROM legacy_horse_odds")
        race_count = scalar(
            con,
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT race_date, race_no
                FROM legacy_horse_odds
                WHERE race_date IS NOT NULL AND race_no IS NOT NULL
            )
            """,
        )
        date_range = dict_or_none(
            con.execute(
                """
                SELECT MIN(race_date) AS minDate, MAX(race_date) AS maxDate
                FROM legacy_horse_odds
                WHERE race_date IS NOT NULL
                """
            ).fetchone()
        )
        odds_type_counts = [
            dict(row)
            for row in con.execute(
                """
                SELECT odds_type AS oddsType, COUNT(*) AS snapshotCount
                FROM legacy_horse_odds
                GROUP BY odds_type
                ORDER BY odds_type
                """
            ).fetchall()
        ]
        duplicate_groups = [
            dict(row)
            for row in con.execute(
                """
                SELECT
                    race_date AS raceDate,
                    race_no AS raceNo,
                    odds_type AS oddsType,
                    odds_value AS oddsValue,
                    snapshot_at AS snapshotAt,
                    source,
                    COUNT(*) AS rowCount,
                    COUNT(DISTINCT odds) AS distinctOddsCount
                FROM legacy_horse_odds
                GROUP BY race_date, race_no, odds_type, odds_value, snapshot_at, source
                HAVING COUNT(*) > 1
                ORDER BY rowCount DESC, race_date DESC, race_no ASC, odds_type ASC, odds_value ASC
                """
            ).fetchall()
        ]
        duplicate_snapshot_count = sum(int(row["rowCount"]) - 1 for row in duplicate_groups)
        critical_missing = {
            "race_date": scalar(con, "SELECT COUNT(*) FROM legacy_horse_odds WHERE race_date IS NULL OR race_date = ''"),
            "race_no": scalar(con, "SELECT COUNT(*) FROM legacy_horse_odds WHERE race_no IS NULL"),
            "odds_type": scalar(con, "SELECT COUNT(*) FROM legacy_horse_odds WHERE odds_type IS NULL OR odds_type = ''"),
            "odds_value": scalar(con, "SELECT COUNT(*) FROM legacy_horse_odds WHERE odds_value IS NULL OR odds_value = ''"),
            "snapshot_at": scalar(con, "SELECT COUNT(*) FROM legacy_horse_odds WHERE snapshot_at IS NULL OR snapshot_at = ''"),
        }
        anomaly_counts = {
            "invalid_odds": scalar(con, "SELECT COUNT(*) FROM legacy_horse_odds WHERE odds IS NULL OR odds <= 1"),
            "missing_implied_probability": scalar(
                con,
                "SELECT COUNT(*) FROM legacy_horse_odds WHERE implied_probability IS NULL AND odds > 1",
            ),
        }
        expected_types = ["win", "fct", "qin", "qpl"]
        present_types = {row["oddsType"] for row in odds_type_counts}
        return {
            "dbPath": str(db_path),
            "tableExists": True,
            "snapshotCount": snapshot_count,
            "raceCount": race_count,
            "dateRange": date_range,
            "oddsTypeCounts": odds_type_counts,
            "expectedOddsTypes": expected_types,
            "missingOddsTypes": [item for item in expected_types if item not in present_types],
            "duplicateGroupCount": len(duplicate_groups),
            "duplicateSnapshotCount": duplicate_snapshot_count,
            "duplicateGroups": duplicate_groups[:100],
            "criticalMissing": critical_missing,
            "anomalyCounts": anomaly_counts,
        }
    finally:
        con.close()


def table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def scalar(con: sqlite3.Connection, sql: str) -> int:
    row = con.execute(sql).fetchone()
    return int(row[0]) if row else 0


def dict_or_none(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit legacy odds snapshots for duplicate business keys.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    report = audit_legacy_odds(args.db)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
