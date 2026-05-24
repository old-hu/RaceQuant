from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import settings


def list_predictions(
    race_date: str | None = None,
    racecourse: str | None = None,
    race_no: int | None = None,
    model_name: str | None = None,
) -> list[dict[str, Any]]:
    db_path = Path(settings.hkjc_structured_db_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[3] / db_path
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    ensure_table(con)
    filters = []
    params: list[Any] = []
    if race_date:
        filters.append("race_date = ?")
        params.append(race_date)
    if racecourse:
        filters.append("racecourse = ?")
        params.append(racecourse.upper())
    if race_no is not None:
        filters.append("race_no = ?")
        params.append(race_no)
    if model_name:
        filters.append("model_name = ?")
        params.append(model_name)
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = con.execute(
        f"""
        SELECT payload_json
        FROM model_predictions
        {where_sql}
        ORDER BY race_date DESC, racecourse, race_no, horse_code
        LIMIT 1000
        """,
        params,
    ).fetchall()
    con.close()
    return [json.loads(row["payload_json"]) for row in rows]


def ensure_table(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS model_predictions (
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            horse_code TEXT NOT NULL,
            model_name TEXT NOT NULL,
            model_version TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (race_date, racecourse, race_no, horse_code, model_name, model_version)
        )
        """
    )
    con.commit()
