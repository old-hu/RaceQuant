from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import settings


def get_connection() -> sqlite3.Connection:
    db_path = Path(settings.legacy_odds_db_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[3] / db_path
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def get_import_status() -> dict[str, Any]:
    with get_connection() as con:
        row = con.execute(
            """
            SELECT
                COUNT(*) AS snapshotCount,
                COUNT(DISTINCT race_date) AS raceDateCount,
                MIN(race_date) AS minRaceDate,
                MAX(race_date) AS maxRaceDate
            FROM legacy_horse_odds
            """
        ).fetchone()
        by_type = con.execute(
            """
            SELECT odds_type AS oddsType, COUNT(*) AS snapshotCount
            FROM legacy_horse_odds
            GROUP BY odds_type
            ORDER BY odds_type
            """
        ).fetchall()
        payload = dict(row)
        payload["byType"] = [dict(item) for item in by_type]
        payload["source"] = "data/processed/legacy_horse_odds.sqlite"
        return payload


def list_snapshots(
    race_date: str | None = None,
    race_no: int | None = None,
    odds_type: str | None = None,
    odds_value: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    filters = []
    params: list[Any] = []
    if race_date:
        filters.append("race_date = ?")
        params.append(race_date)
    if race_no is not None:
        filters.append("race_no = ?")
        params.append(race_no)
    if odds_type:
        filters.append("odds_type = ?")
        params.append(odds_type)
    if odds_value:
        filters.append("odds_value = ?")
        params.append(odds_value)

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.extend([limit, offset])
    with get_connection() as con:
        rows = con.execute(
            f"""
            SELECT
                legacy_id AS legacyId,
                race_date AS raceDate,
                race_no AS raceNo,
                odds_type AS oddsType,
                odds_value AS oddsValue,
                odds,
                implied_probability AS impliedProbability,
                bet_amount AS betAmount,
                snapshot_at AS snapshotAt,
                source
            FROM legacy_horse_odds
            {where_sql}
            ORDER BY race_date DESC, race_no ASC, odds_type ASC, snapshot_at ASC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]


def summarize_snapshots(race_date: str | None = None, race_no: int | None = None) -> list[dict[str, Any]]:
    filters = []
    params: list[Any] = []
    if race_date:
        filters.append("race_date = ?")
        params.append(race_date)
    if race_no is not None:
        filters.append("race_no = ?")
        params.append(race_no)
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_connection() as con:
        rows = con.execute(
            f"""
            SELECT
                race_date AS raceDate,
                race_no AS raceNo,
                odds_type AS oddsType,
                COUNT(*) AS snapshotCount,
                COUNT(DISTINCT odds_value) AS oddsValueCount,
                MIN(snapshot_at) AS firstSnapshotAt,
                MAX(snapshot_at) AS lastSnapshotAt
            FROM legacy_horse_odds
            {where_sql}
            GROUP BY race_date, race_no, odds_type
            ORDER BY race_date DESC, race_no ASC, odds_type ASC
            LIMIT 1000
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]


def list_changes(
    race_date: str,
    race_no: int,
    odds_type: str = "win",
    odds_value: str | None = None,
    limit_values: int = 20,
) -> list[dict[str, Any]]:
    filters = ["race_date = ?", "race_no = ?", "odds_type = ?"]
    params: list[Any] = [race_date, race_no, odds_type]
    if odds_value:
        filters.append("odds_value = ?")
        params.append(odds_value)
    where_sql = f"WHERE {' AND '.join(filters)}"
    with get_connection() as con:
        values = con.execute(
            f"""
            SELECT odds_value AS oddsValue, COUNT(*) AS snapshotCount
            FROM legacy_horse_odds
            {where_sql}
            GROUP BY odds_value
            ORDER BY snapshotCount DESC, odds_value ASC
            LIMIT ?
            """,
            [*params, limit_values],
        ).fetchall()
        series = []
        for value_row in values:
            value = value_row["oddsValue"]
            rows = con.execute(
                f"""
                SELECT
                    legacy_id AS legacyId,
                    race_date AS raceDate,
                    race_no AS raceNo,
                    odds_type AS oddsType,
                    odds_value AS oddsValue,
                    odds,
                    implied_probability AS impliedProbability,
                    bet_amount AS betAmount,
                    snapshot_at AS snapshotAt,
                    source
                FROM legacy_horse_odds
                {where_sql} AND odds_value = ?
                ORDER BY snapshot_at ASC, legacy_id ASC
                """,
                [*params, value],
            ).fetchall()
            points = [dict(row) for row in rows]
            first = points[0]["odds"] if points else None
            last = points[-1]["odds"] if points else None
            series.append(
                {
                    "raceDate": race_date,
                    "raceNo": race_no,
                    "oddsType": odds_type,
                    "oddsValue": value,
                    "snapshotCount": len(points),
                    "firstOdds": first,
                    "lastOdds": last,
                    "change": (last - first) if first is not None and last is not None else None,
                    "points": points,
                }
            )
        return series
