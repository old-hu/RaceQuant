from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import settings


def get_connection() -> sqlite3.Connection:
    db_path = Path(settings.hkjc_structured_db_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[3] / db_path
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def list_races(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as con:
        rows = con.execute(
            """
            SELECT
                rr.race_date AS raceDate,
                rr.racecourse AS racecourse,
                rr.race_no AS raceNo,
                rm.race_index AS raceIndex,
                rm.race_class AS raceClass,
                rm.distance_m AS distanceM,
                rm.going AS going,
                rm.surface AS surface,
                rm.course_layout AS courseLayout,
                rm.race_name AS raceName,
                COUNT(*) AS runnerCount,
                MIN(rr.updated_at) AS firstUpdatedAt,
                MAX(rr.updated_at) AS lastUpdatedAt,
                COALESCE(d.dividendCount, 0) AS dividendCount
            FROM race_results rr
            LEFT JOIN race_metadata rm
                ON rm.race_date = rr.race_date
                AND rm.racecourse = rr.racecourse
                AND rm.race_no = rr.race_no
            LEFT JOIN (
                SELECT race_date, racecourse, race_no, COUNT(*) AS dividendCount
                FROM dividends
                GROUP BY race_date, racecourse, race_no
            ) d
                ON d.race_date = rr.race_date
                AND d.racecourse = rr.racecourse
                AND d.race_no = rr.race_no
            GROUP BY rr.race_date, rr.racecourse, rr.race_no
            ORDER BY rr.race_date DESC, rr.racecourse ASC, rr.race_no ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]


def get_race(race_date: str, racecourse: str, race_no: int) -> dict[str, Any] | None:
    with get_connection() as con:
        row = con.execute(
            """
            SELECT
                rr.race_date AS raceDate,
                rr.racecourse,
                rr.race_no AS raceNo,
                rm.race_index AS raceIndex,
                rm.race_class AS raceClass,
                rm.distance_m AS distanceM,
                rm.rating_range AS ratingRange,
                rm.going,
                rm.race_name AS raceName,
                rm.prize_money AS prizeMoney,
                rm.course,
                rm.surface,
                rm.course_layout AS courseLayout,
                rm.time_text AS timeText,
                rm.sectional_time_text AS sectionalTimeText,
                COUNT(*) AS runnerCount,
                MIN(rr.finish_time) AS fastestFinishTime,
                MAX(rr.updated_at) AS updatedAt
            FROM race_results rr
            LEFT JOIN race_metadata rm
                ON rm.race_date = rr.race_date
                AND rm.racecourse = rr.racecourse
                AND rm.race_no = rr.race_no
            WHERE rr.race_date = ? AND rr.racecourse = ? AND rr.race_no = ?
            GROUP BY rr.race_date, rr.racecourse, rr.race_no
            """,
            (race_date, racecourse.upper(), race_no),
        ).fetchone()
        if row is None:
            return None

        dividends = con.execute(
            """
            SELECT pool, winning_combination AS winningCombination, dividend
            FROM dividends
            WHERE race_date = ? AND racecourse = ? AND race_no = ?
            ORDER BY pool, winning_combination
            """,
            (race_date, racecourse.upper(), race_no),
        ).fetchall()
        payload = dict(row)
        payload["dividends"] = [dict(item) for item in dividends]
        payload["entries"] = list_race_entries(race_date, racecourse, race_no)
        return payload


def list_race_runners(race_date: str, racecourse: str, race_no: int) -> list[dict[str, Any]]:
    with get_connection() as con:
        rows = con.execute(
            """
            SELECT
                race_date AS raceDate,
                racecourse,
                race_no AS raceNo,
                place,
                horse_no AS horseNo,
                horse_name AS horseName,
                horse_code AS horseCode,
                jockey,
                trainer,
                actual_weight AS actualWeight,
                declared_horse_weight AS declaredHorseWeight,
                draw,
                lbw,
                running_position AS runningPosition,
                finish_time AS finishTime,
                win_odds AS winOdds,
                updated_at AS updatedAt
            FROM race_results
            WHERE race_date = ? AND racecourse = ? AND race_no = ?
            ORDER BY CAST(place AS INTEGER), CAST(horse_no AS INTEGER)
            """,
            (race_date, racecourse.upper(), race_no),
        ).fetchall()
        return [dict(row) for row in rows]


def list_race_entries(race_date: str, racecourse: str, race_no: int) -> list[dict[str, Any]]:
    with get_connection() as con:
        if not table_exists(con, "race_entries"):
            return []
        rows = con.execute(
            """
            SELECT
                race_date AS raceDate,
                racecourse,
                race_no AS raceNo,
                horse_no AS horseNo,
                horse_name AS horseName,
                horse_code AS horseCode,
                last_6_runs AS last6Runs,
                actual_weight AS actualWeight,
                jockey,
                draw,
                trainer,
                international_rating AS internationalRating,
                rating,
                rating_change AS ratingChange,
                declared_horse_weight AS declaredHorseWeight,
                horse_weight_change AS horseWeightChange,
                best_time AS bestTime,
                age,
                wfa,
                sex,
                season_stakes AS seasonStakes,
                priority,
                days_since_last_run AS daysSinceLastRun,
                gear,
                owner,
                sire,
                dam,
                import_category AS importCategory,
                standby,
                updated_at AS updatedAt
            FROM race_entries
            WHERE race_date = ? AND racecourse = ? AND race_no = ?
            ORDER BY standby ASC, CAST(horse_no AS INTEGER)
            """,
            (race_date, racecourse.upper(), race_no),
        ).fetchall()
        return [dict(row) for row in rows]


def list_change_events(race_date: str | None = None, race_no: int | None = None, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as con:
        if not table_exists(con, "race_change_events"):
            return []
        filters: list[str] = []
        params: list[Any] = []
        if race_date:
            filters.append("race_date = ?")
            params.append(race_date)
        if race_no is not None:
            filters.append("race_no = ?")
            params.append(race_no)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = con.execute(
            f"""
            SELECT
                race_date AS raceDate,
                race_no AS raceNo,
                sequence,
                event_type AS eventType,
                horse_no AS horseNo,
                horse_name AS horseName,
                related_horse_name AS relatedHorseName,
                jockey,
                declared_weight AS declaredWeight,
                event_time_text AS eventTimeText,
                description,
                updated_at AS updatedAt
            FROM race_change_events
            {where}
            ORDER BY race_date DESC, race_no ASC, sequence ASC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]


def get_horse(horse_code: str) -> dict[str, Any] | None:
    with get_connection() as con:
        row = con.execute(
            """
            SELECT
                horse_code AS horseCode,
                horse_name AS horseName,
                COUNT(*) AS starts,
                SUM(CASE WHEN place = '1' THEN 1 ELSE 0 END) AS wins,
                MIN(race_date) AS firstSeenDate,
                MAX(race_date) AS lastSeenDate,
                MAX(updated_at) AS updatedAt
            FROM race_results
            WHERE horse_code = ?
            GROUP BY horse_code, horse_name
            ORDER BY lastSeenDate DESC
            LIMIT 1
            """,
            (horse_code.upper(),),
        ).fetchone()
        return dict(row) if row else None


def list_horse_history(horse_code: str, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as con:
        if table_exists(con, "horse_form_records"):
            rows = con.execute(
                """
                SELECT
                    horse_code AS horseCode,
                    race_index AS raceIndex,
                    place,
                    race_date AS raceDate,
                    racecourse,
                    track,
                    course,
                    distance_m AS distanceM,
                    going,
                    race_class AS raceClass,
                    draw,
                    rating,
                    trainer,
                    jockey,
                    lbw,
                    win_odds AS winOdds,
                    actual_weight AS actualWeight,
                    running_position AS runningPosition,
                    finish_time AS finishTime,
                    declared_horse_weight AS declaredHorseWeight,
                    gear,
                    season,
                    updated_at AS updatedAt
                FROM horse_form_records
                WHERE horse_code = ?
                ORDER BY race_date DESC, race_index DESC
                LIMIT ? OFFSET ?
                """,
                (horse_code.upper(), limit, offset),
            ).fetchall()
            if rows:
                return [dict(row) for row in rows]
        rows = con.execute(
            """
            SELECT
                race_date AS raceDate,
                racecourse,
                race_no AS raceNo,
                place,
                horse_no AS horseNo,
                horse_name AS horseName,
                horse_code AS horseCode,
                jockey,
                trainer,
                actual_weight AS actualWeight,
                declared_horse_weight AS declaredHorseWeight,
                draw,
                lbw,
                running_position AS runningPosition,
                finish_time AS finishTime,
                win_odds AS winOdds,
                updated_at AS updatedAt
            FROM race_results
            WHERE horse_code = ?
            ORDER BY race_date DESC, racecourse ASC, race_no ASC
            LIMIT ? OFFSET ?
            """,
            (horse_code.upper(), limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]
