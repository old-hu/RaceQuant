from __future__ import annotations

import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal


OddsMode = Literal["none", "pre_start_latest", "result_final"]


@dataclass(frozen=True)
class RunnerFeatureRow:
    race_date: str
    racecourse: str
    race_no: int
    horse_code: str
    horse_no: str
    horse_name: str
    recent_3_starts: int
    recent_3_win_rate: float | None
    recent_3_place_rate: float | None
    recent_3_avg_finish: float | None
    recent_5_starts: int
    recent_5_win_rate: float | None
    recent_5_place_rate: float | None
    recent_5_avg_finish: float | None
    days_since_last_run: int | None
    draw: int | None
    draw_bucket: str | None
    actual_weight_lbs: int | None
    declared_horse_weight_lbs: int | None
    jockey_win_rate: float | None
    trainer_win_rate: float | None
    win_odds: float | None
    implied_win_probability: float | None
    distance_m: int | None
    distance_starts: int
    distance_win_rate: float | None
    surface: str | None
    going: str | None
    surface_starts: int
    surface_win_rate: float | None
    class_change: str | None


class FeatureEngine:
    def __init__(
        self,
        db_path: Path,
        odds_mode: OddsMode = "none",
        odds_db_path: Path | None = None,
    ) -> None:
        self.db_path = db_path
        self.odds_mode = odds_mode
        self.odds_db_path = odds_db_path or Path("data/processed/legacy_horse_odds.sqlite")

    def build_runner_features(
        self,
        race_date: str | None = None,
        racecourse: str | None = None,
        race_no: int | None = None,
        limit: int = 5000,
    ) -> list[RunnerFeatureRow]:
        with self._connect() as con:
            current_rows = self._current_rows(con, race_date, racecourse, race_no, limit)
            return [self._build_row(con, row) for row in current_rows]

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _current_rows(
        self,
        con: sqlite3.Connection,
        race_date: str | None,
        racecourse: str | None,
        race_no: int | None,
        limit: int,
    ) -> list[sqlite3.Row]:
        filters = ["horse_code IS NOT NULL"]
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
        params.append(limit)
        return con.execute(
            f"""
            SELECT *
            FROM race_results
            WHERE {' AND '.join(filters)}
            ORDER BY race_date DESC, racecourse ASC, race_no ASC, CAST(place AS INTEGER)
            LIMIT ?
            """,
            params,
        ).fetchall()

    def _build_row(self, con: sqlite3.Connection, row: sqlite3.Row) -> RunnerFeatureRow:
        history = con.execute(
            """
            SELECT *
            FROM race_results
            WHERE horse_code = ?
              AND (
                race_date < ?
                OR (race_date = ? AND racecourse < ?)
                OR (race_date = ? AND racecourse = ? AND race_no < ?)
              )
            ORDER BY race_date DESC, racecourse DESC, race_no DESC
            LIMIT 5
            """,
            (
                row["horse_code"],
                row["race_date"],
                row["race_date"],
                row["racecourse"],
                row["race_date"],
                row["racecourse"],
                row["race_no"],
            ),
        ).fetchall()
        recent_3 = history[:3]
        recent_5 = history[:5]
        jockey_stats = self._person_stats(con, "jockey", row["jockey"], row["race_date"])
        trainer_stats = self._person_stats(con, "trainer", row["trainer"], row["race_date"])
        metadata = self._metadata(con, row)
        distance_stats = self._metadata_stats(con, row, "distance_m", metadata["distance_m"] if metadata else None)
        surface_stats = self._metadata_stats(con, row, "surface", metadata["surface"] if metadata else None)
        win_odds = self._win_odds(con, row)

        return RunnerFeatureRow(
            race_date=row["race_date"],
            racecourse=row["racecourse"],
            race_no=int(row["race_no"]),
            horse_code=row["horse_code"],
            horse_no=row["horse_no"],
            horse_name=row["horse_name"],
            recent_3_starts=len(recent_3),
            recent_3_win_rate=win_rate(recent_3),
            recent_3_place_rate=place_rate(recent_3),
            recent_3_avg_finish=avg_finish(recent_3),
            recent_5_starts=len(recent_5),
            recent_5_win_rate=win_rate(recent_5),
            recent_5_place_rate=place_rate(recent_5),
            recent_5_avg_finish=avg_finish(recent_5),
            days_since_last_run=days_between(history[0]["race_date"], row["race_date"]) if history else None,
            draw=parse_int(row["draw"]),
            draw_bucket=draw_bucket(parse_int(row["draw"])),
            actual_weight_lbs=parse_int(row["actual_weight"]),
            declared_horse_weight_lbs=parse_int(row["declared_horse_weight"]),
            jockey_win_rate=jockey_stats,
            trainer_win_rate=trainer_stats,
            win_odds=win_odds,
            implied_win_probability=(1 / win_odds) if win_odds and win_odds > 0 else None,
            distance_m=metadata["distance_m"] if metadata else None,
            distance_starts=distance_stats["starts"],
            distance_win_rate=distance_stats["win_rate"],
            surface=metadata["surface"] if metadata else None,
            going=metadata["going"] if metadata else None,
            surface_starts=surface_stats["starts"],
            surface_win_rate=surface_stats["win_rate"],
            class_change=self._class_change(con, row, metadata["race_class"] if metadata else None),
        )

    def _win_odds(self, con: sqlite3.Connection, row: sqlite3.Row) -> float | None:
        if self.odds_mode == "none":
            return None
        if self.odds_mode == "result_final":
            return parse_float(row["win_odds"])
        if self.odds_mode == "pre_start_latest":
            return self._latest_pre_start_win_odds(con, row)
        return None

    def _latest_pre_start_win_odds(self, con: sqlite3.Connection, row: sqlite3.Row) -> float | None:
        # If legacy odds were attached to the structured DB, use them directly.
        if table_exists(con, "legacy_horse_odds"):
            odds = latest_legacy_win_odds(
                con,
                race_date=row["race_date"],
                race_no=int(row["race_no"]),
                odds_value=str(row["horse_no"]),
            )
            if odds is not None:
                return odds
        if not self.odds_db_path.exists():
            return None
        legacy = sqlite3.connect(self.odds_db_path)
        legacy.row_factory = sqlite3.Row
        try:
            return latest_legacy_win_odds(
                legacy,
                race_date=row["race_date"],
                race_no=int(row["race_no"]),
                odds_value=str(row["horse_no"]),
            )
        finally:
            legacy.close()

    def _person_stats(self, con: sqlite3.Connection, column: str, name: str | None, before_date: str) -> float | None:
        if not name:
            return None
        row = con.execute(
            f"""
            SELECT
                COUNT(*) AS starts,
                SUM(CASE WHEN place = '1' THEN 1 ELSE 0 END) AS wins
            FROM race_results
            WHERE {column} = ? AND race_date < ?
            """,
            (name, before_date),
        ).fetchone()
        if not row or row["starts"] == 0:
            return None
        return row["wins"] / row["starts"]

    def _metadata(self, con: sqlite3.Connection, row: sqlite3.Row) -> sqlite3.Row | None:
        return con.execute(
            """
            SELECT *
            FROM race_metadata
            WHERE race_date = ? AND racecourse = ? AND race_no = ?
            """,
            (row["race_date"], row["racecourse"], row["race_no"]),
        ).fetchone()

    def _metadata_stats(
        self,
        con: sqlite3.Connection,
        row: sqlite3.Row,
        metadata_column: str,
        metadata_value: Any,
    ) -> dict[str, float | int | None]:
        if metadata_value in (None, ""):
            return {"starts": 0, "win_rate": None}
        result = con.execute(
            f"""
            SELECT
                COUNT(*) AS starts,
                SUM(CASE WHEN rr.place = '1' THEN 1 ELSE 0 END) AS wins
            FROM race_results rr
            JOIN race_metadata rm
                ON rm.race_date = rr.race_date
                AND rm.racecourse = rr.racecourse
                AND rm.race_no = rr.race_no
            WHERE rr.horse_code = ?
              AND rm.{metadata_column} = ?
              AND rr.race_date < ?
            """,
            (row["horse_code"], metadata_value, row["race_date"]),
        ).fetchone()
        starts = int(result["starts"]) if result else 0
        wins = int(result["wins"] or 0) if result else 0
        return {"starts": starts, "win_rate": (wins / starts) if starts else None}

    def _class_change(self, con: sqlite3.Connection, row: sqlite3.Row, current_class: str | None) -> str | None:
        if not current_class:
            return None
        previous = con.execute(
            """
            SELECT rm.race_class
            FROM race_results rr
            JOIN race_metadata rm
                ON rm.race_date = rr.race_date
                AND rm.racecourse = rr.racecourse
                AND rm.race_no = rr.race_no
            WHERE rr.horse_code = ? AND rr.race_date < ?
            ORDER BY rr.race_date DESC, rr.racecourse DESC, rr.race_no DESC
            LIMIT 1
            """,
            (row["horse_code"], row["race_date"]),
        ).fetchone()
        if not previous or not previous["race_class"]:
            return None
        current_no = parse_class_number(current_class)
        previous_no = parse_class_number(previous["race_class"])
        if current_no is None or previous_no is None:
            return "same" if previous["race_class"] == current_class else "changed"
        if current_no < previous_no:
            return "up"
        if current_no > previous_no:
            return "down"
        return "same"


def win_rate(rows: list[sqlite3.Row]) -> float | None:
    if not rows:
        return None
    return sum(1 for row in rows if row["place"] == "1") / len(rows)


def place_rate(rows: list[sqlite3.Row]) -> float | None:
    if not rows:
        return None
    return sum(1 for row in rows if parse_int(row["place"]) and parse_int(row["place"]) <= 3) / len(rows)


def avg_finish(rows: list[sqlite3.Row]) -> float | None:
    places = [parse_int(row["place"]) for row in rows]
    places = [place for place in places if place is not None]
    return (sum(places) / len(places)) if places else None


def days_between(previous: str, current: str) -> int:
    return (date.fromisoformat(current) - date.fromisoformat(previous)).days


def parse_int(value: Any) -> int | None:
    try:
        if value in (None, "", "-", "---"):
            return None
        return int(str(value))
    except ValueError:
        return None


def parse_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-", "---"):
            return None
        parsed = float(str(value))
        if math.isfinite(parsed):
            return parsed
    except ValueError:
        return None
    return None


def draw_bucket(draw: int | None) -> str | None:
    if draw is None:
        return None
    if draw <= 4:
        return "inside"
    if draw <= 8:
        return "middle"
    return "outside"


def parse_class_number(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"Class\s+(\d+)", value, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def latest_legacy_win_odds(
    con: sqlite3.Connection,
    race_date: str,
    race_no: int,
    odds_value: str,
) -> float | None:
    if not table_exists(con, "legacy_horse_odds"):
        return None
    cutoff_at = historical_odds_cutoff_at(con, race_date, race_no)
    if cutoff_at is None:
        return None
    row = con.execute(
        """
        SELECT odds
        FROM legacy_horse_odds
        WHERE race_date = ?
          AND race_no = ?
          AND odds_type = 'win'
          AND odds_value = ?
          AND snapshot_at IS NOT NULL
          AND snapshot_at <= ?
        ORDER BY snapshot_at DESC, legacy_id DESC
        LIMIT 1
        """,
        (race_date, race_no, odds_value, cutoff_at),
    ).fetchone()
    return parse_float(row["odds"]) if row else None


def historical_odds_cutoff_at(con: sqlite3.Connection, race_date: str, race_no: int) -> str | None:
    row = con.execute(
        """
        SELECT MAX(snapshot_at) AS final_snapshot_at
        FROM legacy_horse_odds
        WHERE race_date = ?
          AND race_no = ?
          AND odds_type = 'win'
          AND snapshot_at IS NOT NULL
        """,
        (race_date, race_no),
    ).fetchone()
    if not row or not row["final_snapshot_at"]:
        return None
    final_snapshot = parse_iso_datetime(row["final_snapshot_at"])
    if final_snapshot is None:
        return None
    cutoff = final_snapshot - timedelta(minutes=1)
    return cutoff.replace(microsecond=0).isoformat()[:19]


def parse_iso_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip().replace(" ", "T")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None
