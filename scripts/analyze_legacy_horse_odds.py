import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymysql


SELECTED_ODDS_TYPES = ("win", "fct", "qin", "qpl")


def normalize(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.getenv("LEGACY_DB_HOST", "192.168.3.244"),
        port=int(os.getenv("LEGACY_DB_PORT", "3306")),
        user=os.getenv("LEGACY_DB_USER", "root"),
        password=os.environ["LEGACY_DB_PASSWORD"],
        database=os.getenv("LEGACY_DB_NAME", "digit-ai"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=120,
    )


def main() -> None:
    output_path = Path("data/reports/legacy_horse_odds_analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (os.getenv("LEGACY_DB_NAME", "digit-ai"), "horse_odds"),
            )
            columns = cur.fetchall()

            cur.execute(
                """
                SELECT INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME, CARDINALITY
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """,
                (os.getenv("LEGACY_DB_NAME", "digit-ai"), "horse_odds"),
            )
            indexes = cur.fetchall()

            cur.execute(
                """
                SELECT TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH, CREATE_TIME, UPDATE_TIME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """,
                (os.getenv("LEGACY_DB_NAME", "digit-ai"), "horse_odds"),
            )
            table_stats = cur.fetchone()

            cur.execute("SELECT MIN(race_date) AS min_date, MAX(race_date) AS max_date FROM horse_odds")
            date_range = cur.fetchone()

            cur.execute(
                """
                SELECT race_date, COUNT(*) AS selected_rows
                FROM horse_odds FORCE INDEX (idx_horse_odds_race_date_race_no)
                WHERE odds_type IN %s
                GROUP BY race_date
                ORDER BY race_date
                """,
                (SELECTED_ODDS_TYPES,),
            )
            selected_rows_by_date = cur.fetchall()

            samples = []
            for odds_type in SELECTED_ODDS_TYPES:
                cur.execute("SELECT * FROM horse_odds WHERE odds_type = %s LIMIT 3", (odds_type,))
                samples.extend(cur.fetchall())

    output = {
        "table": "horse_odds",
        "selected_odds_types": SELECTED_ODDS_TYPES,
        "columns": columns,
        "indexes": indexes,
        "table_stats": table_stats,
        "date_range": date_range,
        "selected_rows_by_date": selected_rows_by_date,
        "samples": samples,
    }
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=normalize), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

