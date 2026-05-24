import argparse
import json
import sqlite3
from pathlib import Path

from hkjc_structured_store import STRUCTURED_DB, connect


def main() -> None:
    parser = argparse.ArgumentParser(description="导出结构化落库数据，供前端展示。")
    parser.add_argument("--db", type=Path, default=STRUCTURED_DB)
    parser.add_argument("--output-dir", type=Path, default=Path("frontend/public/data"))
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    con = connect(args.db)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    write_json(args.output_dir / "structured-results.json", query_rows(con, RESULTS_SQL, args.limit))
    write_json(args.output_dir / "structured-dividends.json", query_rows(con, DIVIDENDS_SQL, args.limit))
    write_json(args.output_dir / "structured-races.json", query_rows(con, RACES_SQL, args.limit))
    write_json(args.output_dir / "structured-entries.json", query_rows(con, ENTRIES_SQL, args.limit))
    write_json(args.output_dir / "structured-horse-profiles.json", query_rows(con, HORSE_PROFILES_SQL, args.limit))
    write_json(args.output_dir / "structured-horse-form-records.json", query_rows(con, HORSE_FORM_RECORDS_SQL, args.limit))
    write_json(args.output_dir / "structured-change-events.json", query_rows(con, CHANGE_EVENTS_SQL, args.limit))
    write_json(args.output_dir / "scrape-jobs.json", query_rows(con, JOBS_SQL, args.limit))
    con.close()
    print(f"Wrote structured data exports to {args.output_dir}")


def query_rows(con: sqlite3.Connection, sql: str, limit: int) -> list[dict[str, object]]:
    return [dict(row) for row in con.execute(sql, {"limit": limit}).fetchall()]


def write_json(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


RESULTS_SQL = """
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
    draw,
    lbw,
    finish_time AS finishTime,
    win_odds AS winOdds,
    updated_at AS updatedAt
FROM race_results
ORDER BY race_date DESC, racecourse, race_no, CAST(place AS INTEGER)
LIMIT :limit
"""

DIVIDENDS_SQL = """
SELECT
    race_date AS raceDate,
    racecourse,
    race_no AS raceNo,
    pool,
    winning_combination AS winningCombination,
    dividend,
    updated_at AS updatedAt
FROM dividends
ORDER BY race_date DESC, racecourse, race_no, pool
LIMIT :limit
"""

JOBS_SQL = """
SELECT
    race_date AS raceDate,
    racecourse,
    status,
    attempts,
    started_at AS startedAt,
    finished_at AS finishedAt,
    last_error AS lastError
FROM scrape_jobs
ORDER BY race_date DESC, racecourse
LIMIT :limit
"""

RACES_SQL = """
SELECT
    race_date AS raceDate,
    racecourse,
    race_no AS raceNo,
    race_index AS raceIndex,
    race_class AS raceClass,
    distance_m AS distanceM,
    rating_range AS ratingRange,
    going,
    race_name AS raceName,
    prize_money AS prizeMoney,
    course,
    surface,
    course_layout AS courseLayout,
    time_text AS timeText,
    sectional_time_text AS sectionalTimeText,
    updated_at AS updatedAt
FROM race_metadata
ORDER BY race_date DESC, racecourse, race_no
LIMIT :limit
"""

ENTRIES_SQL = """
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
ORDER BY race_date DESC, racecourse, race_no, standby, CAST(horse_no AS INTEGER)
LIMIT :limit
"""

HORSE_PROFILES_SQL = """
SELECT
    horse_code AS horseCode,
    horse_name AS horseName,
    country,
    age,
    colour,
    sex,
    import_type AS importType,
    season_stakes AS seasonStakes,
    total_stakes AS totalStakes,
    starts_summary AS startsSummary,
    starts_past_10_meetings AS startsPast10Meetings,
    current_location AS currentLocation,
    import_date AS importDate,
    trainer,
    owner,
    current_rating AS currentRating,
    start_of_season_rating AS startOfSeasonRating,
    sire,
    dam,
    dam_sire AS damSire,
    same_sire AS sameSire,
    updated_at AS updatedAt
FROM horse_profiles
ORDER BY horse_code
LIMIT :limit
"""

HORSE_FORM_RECORDS_SQL = """
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
ORDER BY horse_code, race_date DESC, race_index DESC
LIMIT :limit
"""

CHANGE_EVENTS_SQL = """
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
ORDER BY race_date DESC, race_no, sequence
LIMIT :limit
"""


if __name__ == "__main__":
    main()
