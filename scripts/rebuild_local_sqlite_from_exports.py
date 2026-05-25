from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_EXPORTS_DIR = ROOT_DIR / "frontend" / "public" / "data"
DEFAULT_STRUCTURED_DB = ROOT_DIR / "data" / "processed" / "hkjc_structured.sqlite"
DEFAULT_ODDS_DB = ROOT_DIR / "data" / "processed" / "legacy_horse_odds.sqlite"

sys.path.insert(0, str(SCRIPT_DIR))
from hkjc_structured_store import connect as connect_structured  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild local SQLite databases from frontend JSON exports."
    )
    parser.add_argument("--exports-dir", type=Path, default=DEFAULT_EXPORTS_DIR)
    parser.add_argument("--structured-db", type=Path, default=DEFAULT_STRUCTURED_DB)
    parser.add_argument("--odds-db", type=Path, default=DEFAULT_ODDS_DB)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing local SQLite files before rebuilding them.",
    )
    args = parser.parse_args()

    exports_dir = args.exports_dir.resolve()
    structured_db = args.structured_db.resolve()
    odds_db = args.odds_db.resolve()

    if args.reset:
        for path in (structured_db, odds_db):
            reset_sqlite_database(path)

    structured_counts = rebuild_structured_db(exports_dir, structured_db)
    odds_counts = rebuild_odds_db(exports_dir, odds_db)
    print(
        json.dumps(
            {
                "structuredDb": str(structured_db),
                "structuredCounts": structured_counts,
                "oddsDb": str(odds_db),
                "oddsCounts": odds_counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def load_json(exports_dir: Path, filename: str) -> Any:
    path = exports_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing export file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def value(row: dict[str, Any], key: str, default: Any = None) -> Any:
    return row.get(key, default)


def reset_sqlite_database(path: Path) -> None:
    if not path.exists():
        return
    try:
        path.unlink()
        return
    except PermissionError:
        pass

    con = sqlite3.connect(path)
    try:
        table_names = [
            row[0]
            for row in con.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        ]
        con.execute("PRAGMA foreign_keys = OFF")
        for table_name in table_names:
            con.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        con.commit()
    finally:
        con.close()


def rebuild_structured_db(exports_dir: Path, db_path: Path) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = connect_structured(db_path)
    source_prefix = "frontend/public/data"
    try:
        upsert_race_metadata(con, load_json(exports_dir, "structured-races.json"), source_prefix)
        upsert_race_results(con, load_json(exports_dir, "structured-results.json"), source_prefix)
        upsert_race_entries(con, load_json(exports_dir, "structured-entries.json"), source_prefix)
        upsert_dividends(con, load_json(exports_dir, "structured-dividends.json"), source_prefix)
        upsert_change_events(con, load_json(exports_dir, "structured-change-events.json"), source_prefix)
        upsert_horse_profiles(con, load_json(exports_dir, "structured-horse-profiles.json"), source_prefix)
        upsert_horse_form_records(con, load_json(exports_dir, "structured-horse-form-records.json"), source_prefix)
        upsert_scrape_jobs(con, load_json(exports_dir, "scrape-jobs.json"))
        upsert_model_predictions(con, load_json(exports_dir, "baseline_predictions.json"))
        con.commit()
        return table_counts(
            con,
            [
                "race_metadata",
                "race_results",
                "race_entries",
                "dividends",
                "race_change_events",
                "horse_profiles",
                "horse_form_records",
                "scrape_jobs",
                "model_predictions",
            ],
        )
    finally:
        con.close()


def upsert_race_metadata(con: sqlite3.Connection, rows: list[dict[str, Any]], source_prefix: str) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO race_metadata (
            race_date, racecourse, race_no, race_index, race_class, distance_m,
            rating_range, going, race_name, prize_money, course, surface,
            course_layout, time_text, sectional_time_text, source_path, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["raceDate"],
                row["racecourse"],
                int(row["raceNo"]),
                value(row, "raceIndex"),
                value(row, "raceClass"),
                value(row, "distanceM"),
                value(row, "ratingRange"),
                value(row, "going"),
                value(row, "raceName"),
                value(row, "prizeMoney"),
                value(row, "course"),
                value(row, "surface"),
                value(row, "courseLayout"),
                value(row, "timeText"),
                value(row, "sectionalTimeText"),
                f"{source_prefix}/structured-races.json",
                value(row, "updatedAt", ""),
            )
            for row in rows
        ],
    )


def upsert_race_results(con: sqlite3.Connection, rows: list[dict[str, Any]], source_prefix: str) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO race_results (
            race_date, racecourse, race_no, place, horse_no, horse_name, horse_code,
            jockey, trainer, actual_weight, declared_horse_weight, draw, lbw,
            running_position, finish_time, win_odds, source_path, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["raceDate"],
                row["racecourse"],
                int(row["raceNo"]),
                str(row["place"]),
                value(row, "horseNo"),
                value(row, "horseName"),
                value(row, "horseCode"),
                value(row, "jockey"),
                value(row, "trainer"),
                value(row, "actualWeight"),
                value(row, "declaredHorseWeight"),
                value(row, "draw"),
                value(row, "lbw"),
                value(row, "runningPosition"),
                value(row, "finishTime"),
                value(row, "winOdds"),
                f"{source_prefix}/structured-results.json",
                value(row, "updatedAt", ""),
            )
            for row in rows
        ],
    )


def upsert_race_entries(con: sqlite3.Connection, rows: list[dict[str, Any]], source_prefix: str) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO race_entries (
            race_date, racecourse, race_no, horse_no, horse_name, horse_code, last_6_runs,
            actual_weight, jockey, draw, trainer, international_rating, rating, rating_change,
            declared_horse_weight, horse_weight_change, best_time, age, wfa, sex, season_stakes,
            priority, days_since_last_run, gear, owner, sire, dam, import_category, standby,
            source_path, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["raceDate"],
                row["racecourse"],
                int(row["raceNo"]),
                str(row["horseNo"]),
                value(row, "horseName"),
                value(row, "horseCode"),
                value(row, "last6Runs"),
                value(row, "actualWeight"),
                value(row, "jockey"),
                value(row, "draw"),
                value(row, "trainer"),
                value(row, "internationalRating"),
                value(row, "rating"),
                value(row, "ratingChange"),
                value(row, "declaredHorseWeight"),
                value(row, "horseWeightChange"),
                value(row, "bestTime"),
                value(row, "age"),
                value(row, "wfa"),
                value(row, "sex"),
                value(row, "seasonStakes"),
                value(row, "priority"),
                value(row, "daysSinceLastRun"),
                value(row, "gear"),
                value(row, "owner"),
                value(row, "sire"),
                value(row, "dam"),
                value(row, "importCategory"),
                int(value(row, "standby", 0) or 0),
                f"{source_prefix}/structured-entries.json",
                value(row, "updatedAt", ""),
            )
            for row in rows
        ],
    )


def upsert_dividends(con: sqlite3.Connection, rows: list[dict[str, Any]], source_prefix: str) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO dividends (
            race_date, racecourse, race_no, pool, winning_combination, dividend, source_path, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["raceDate"],
                value(row, "racecourse"),
                int(row["raceNo"]),
                row["pool"],
                row["winningCombination"],
                str(row["dividend"]),
                f"{source_prefix}/structured-dividends.json",
                value(row, "updatedAt", ""),
            )
            for row in rows
        ],
    )


def upsert_change_events(con: sqlite3.Connection, rows: list[dict[str, Any]], source_prefix: str) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO race_change_events (
            race_date, race_no, sequence, event_type, horse_no, horse_name, related_horse_name,
            jockey, declared_weight, event_time_text, description, source_path, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["raceDate"],
                int(row["raceNo"]),
                int(row["sequence"]),
                row["eventType"],
                value(row, "horseNo"),
                value(row, "horseName"),
                value(row, "relatedHorseName"),
                value(row, "jockey"),
                value(row, "declaredWeight"),
                value(row, "eventTimeText"),
                row["description"],
                f"{source_prefix}/structured-change-events.json",
                value(row, "updatedAt", ""),
            )
            for row in rows
        ],
    )


def upsert_horse_profiles(con: sqlite3.Connection, rows: list[dict[str, Any]], source_prefix: str) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO horse_profiles (
            horse_code, horse_name, country, age, colour, sex, import_type, season_stakes,
            total_stakes, starts_summary, starts_past_10_meetings, current_location, import_date,
            trainer, owner, current_rating, start_of_season_rating, sire, dam, dam_sire,
            same_sire, source_path, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["horseCode"],
                value(row, "horseName"),
                value(row, "country"),
                value(row, "age"),
                value(row, "colour"),
                value(row, "sex"),
                value(row, "importType"),
                value(row, "seasonStakes"),
                value(row, "totalStakes"),
                value(row, "startsSummary"),
                value(row, "startsPast10Meetings"),
                value(row, "currentLocation"),
                value(row, "importDate"),
                value(row, "trainer"),
                value(row, "owner"),
                value(row, "currentRating"),
                value(row, "startOfSeasonRating"),
                value(row, "sire"),
                value(row, "dam"),
                value(row, "damSire"),
                value(row, "sameSire"),
                f"{source_prefix}/structured-horse-profiles.json",
                value(row, "updatedAt", ""),
            )
            for row in rows
        ],
    )


def upsert_horse_form_records(con: sqlite3.Connection, rows: list[dict[str, Any]], source_prefix: str) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO horse_form_records (
            horse_code, race_index, place, race_date, racecourse, track, course, distance_m,
            going, race_class, draw, rating, trainer, jockey, lbw, win_odds, actual_weight,
            running_position, finish_time, declared_horse_weight, gear, season, source_path, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["horseCode"],
                row["raceIndex"],
                value(row, "place"),
                value(row, "raceDate"),
                value(row, "racecourse"),
                value(row, "track"),
                value(row, "course"),
                value(row, "distanceM"),
                value(row, "going"),
                value(row, "raceClass"),
                value(row, "draw"),
                value(row, "rating"),
                value(row, "trainer"),
                value(row, "jockey"),
                value(row, "lbw"),
                value(row, "winOdds"),
                value(row, "actualWeight"),
                value(row, "runningPosition"),
                value(row, "finishTime"),
                value(row, "declaredHorseWeight"),
                value(row, "gear"),
                value(row, "season"),
                f"{source_prefix}/structured-horse-form-records.json",
                value(row, "updatedAt", ""),
            )
            for row in rows
        ],
    )


def upsert_scrape_jobs(con: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO scrape_jobs (
            race_date, racecourse, status, attempts, started_at, finished_at, last_error, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        [
            (
                row["raceDate"],
                row["racecourse"],
                row["status"],
                int(value(row, "attempts", 0) or 0),
                value(row, "startedAt"),
                value(row, "finishedAt"),
                value(row, "lastError"),
            )
            for row in rows
        ],
    )


def upsert_model_predictions(con: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
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
    con.executemany(
        """
        INSERT OR REPLACE INTO model_predictions (
            race_date, racecourse, race_no, horse_code, model_name, model_version, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["raceDate"],
                row["racecourse"],
                int(row["raceNo"]),
                row["horseCode"],
                row["modelName"],
                row["modelVersion"],
                json.dumps(row, ensure_ascii=False),
            )
            for row in rows
        ],
    )


def rebuild_odds_db(exports_dir: Path, db_path: Path) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    report = load_json(exports_dir, "odds_changes.json")
    con = sqlite3.connect(db_path)
    try:
        con.executescript(
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
            );

            CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_race
            ON legacy_horse_odds (race_date, race_no, odds_type);

            CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_snapshot
            ON legacy_horse_odds (snapshot_at);

            CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_win_lookup
            ON legacy_horse_odds (race_date, race_no, odds_type, odds_value, snapshot_at DESC, legacy_id DESC);

            CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_final_snapshot
            ON legacy_horse_odds (race_date, race_no, odds_type, snapshot_at DESC);
            """
        )
        rows = []
        for series in report.get("series", []):
            for point in series.get("points", []):
                rows.append(
                    (
                        str(point["legacyId"]),
                        point.get("raceDate"),
                        int(point["raceNo"]) if point.get("raceNo") is not None else None,
                        point.get("oddsType"),
                        str(point.get("oddsValue")),
                        float(point.get("odds")),
                        point.get("impliedProbability"),
                        point.get("betAmount"),
                        None,
                        point.get("snapshotAt"),
                        point.get("snapshotAt"),
                        point.get("snapshotAt"),
                        point.get("source") or "frontend/public/data/odds_changes.json",
                    )
                )
        con.executemany(
            """
            INSERT OR REPLACE INTO legacy_horse_odds (
                legacy_id, race_date, race_no, odds_type, odds_value, odds,
                implied_probability, bet_amount, remark, snapshot_at, create_time, update_time, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()
        return table_counts(con, ["legacy_horse_odds"])
    finally:
        con.close()


def table_counts(con: sqlite3.Connection, table_names: list[str]) -> dict[str, int]:
    return {
        table_name: int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
        for table_name in table_names
    }


if __name__ == "__main__":
    main()
