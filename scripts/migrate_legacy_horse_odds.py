import argparse
import os
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import pymysql


SELECTED_ODDS_TYPES = ("win", "fct", "qin", "qpl")


def connect_mysql() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.getenv("LEGACY_DB_HOST", "192.168.3.244"),
        port=int(os.getenv("LEGACY_DB_PORT", "3306")),
        user=os.getenv("LEGACY_DB_USER", "root"),
        password=os.environ["LEGACY_DB_PASSWORD"],
        database=os.getenv("LEGACY_DB_NAME", "digit-ai"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.SSDictCursor,
        connect_timeout=10,
        read_timeout=300,
    )


def normalize_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def implied_probability(odds: Any) -> float | None:
    if odds is None:
        return None
    value = Decimal(str(odds))
    if value <= Decimal("1"):
        return None
    return float((Decimal("1") / value).quantize(Decimal("0.000001")))


def create_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS legacy_horse_odds (
            legacy_id TEXT PRIMARY KEY,
            race_date TEXT,
            race_no INTEGER,
            odds_type TEXT NOT NULL,
            odds_value TEXT NOT NULL,
            odds REAL NOT NULL,
            implied_probability REAL,
            bet_amount REAL,
            remark TEXT,
            snapshot_at TEXT,
            create_time TEXT,
            update_time TEXT,
            source TEXT NOT NULL DEFAULT 'digit-ai.horse_odds'
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_race
        ON legacy_horse_odds (race_date, race_no, odds_type)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_snapshot
        ON legacy_horse_odds (snapshot_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_win_lookup
        ON legacy_horse_odds (race_date, race_no, odds_type, odds_value, snapshot_at DESC, legacy_id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_final_snapshot
        ON legacy_horse_odds (race_date, race_no, odds_type, snapshot_at DESC)
        """
    )
    conn.commit()


def selected_race_dates(conn: pymysql.connections.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT race_date
            FROM horse_odds FORCE INDEX (idx_horse_odds_race_date_race_no)
            WHERE odds_type IN %s
            GROUP BY race_date
            ORDER BY race_date
            """,
            (SELECTED_ODDS_TYPES,),
        )
        return [normalize_datetime(row["race_date"]) for row in cur.fetchall()]


def fetch_rows_for_date(conn: pymysql.connections.Connection, race_date_value: str) -> Iterable[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                race_date,
                race_no,
                odds_type,
                odds_value,
                odds,
                bet_amount,
                remark,
                create_time,
                update_time,
                COALESCE(update_time, create_time) AS snapshot_at
            FROM horse_odds FORCE INDEX (idx_horse_odds_race_date_race_no)
            WHERE race_date = %s
              AND odds_type IN %s
              AND odds IS NOT NULL
              AND odds > 1
              AND odds_value IS NOT NULL
            ORDER BY race_no, odds_type, id
            """,
            (race_date_value, SELECTED_ODDS_TYPES),
        )
        for row in cur:
            yield row


def migrate(output_path: Path, limit_dates: int | None = None) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "output_path": str(output_path),
        "selected_odds_types": list(SELECTED_ODDS_TYPES),
        "dates_processed": 0,
        "rows_inserted": 0,
        "rows_skipped_duplicate": 0,
        "date_summaries": [],
    }

    with connect_mysql() as mysql_conn, sqlite3.connect(output_path) as sqlite_conn:
        create_sqlite_schema(sqlite_conn)
        dates = selected_race_dates(mysql_conn)
        if limit_dates is not None:
            dates = dates[:limit_dates]

        insert_sql = """
            INSERT OR IGNORE INTO legacy_horse_odds (
                legacy_id, race_date, race_no, odds_type, odds_value, odds,
                implied_probability, bet_amount, remark, snapshot_at, create_time, update_time, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        for race_date_value in dates:
            before_changes = sqlite_conn.total_changes
            date_rows = 0
            batch = []

            for row in fetch_rows_for_date(mysql_conn, race_date_value):
                batch.append(
                    (
                        row["id"],
                        normalize_datetime(row["race_date"]),
                        row["race_no"],
                        row["odds_type"],
                        row["odds_value"],
                        row["odds"],
                        implied_probability(row["odds"]),
                        row["bet_amount"],
                        row["remark"],
                        normalize_datetime(row["snapshot_at"]),
                        normalize_datetime(row["create_time"]),
                        normalize_datetime(row["update_time"]),
                        "digit-ai.horse_odds",
                    )
                )
                date_rows += 1

                if len(batch) >= 5000:
                    sqlite_conn.executemany(insert_sql, batch)
                    sqlite_conn.commit()
                    batch.clear()

            if batch:
                sqlite_conn.executemany(insert_sql, batch)
                sqlite_conn.commit()

            inserted = sqlite_conn.total_changes - before_changes
            report["dates_processed"] += 1
            report["rows_inserted"] += inserted
            report["rows_skipped_duplicate"] += max(date_rows - inserted, 0)
            report["date_summaries"].append(
                {
                    "race_date": race_date_value,
                    "source_rows": date_rows,
                    "inserted_rows": inserted,
                    "duplicate_rows": max(date_rows - inserted, 0),
                }
            )
            print(f"{race_date_value}: source={date_rows}, inserted={inserted}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate selected legacy horse odds from MySQL to local SQLite.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/legacy_horse_odds.sqlite"),
        help="SQLite output path.",
    )
    parser.add_argument("--limit-dates", type=int, help="Only migrate the first N race dates.")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("data/reports/legacy_horse_odds_migration_report.json"),
        help="JSON report path.",
    )
    args = parser.parse_args()

    report = migrate(args.output, args.limit_dates)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    import json

    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
