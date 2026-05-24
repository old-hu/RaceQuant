from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


STRUCTURED_DB = Path("data/processed/hkjc_structured.sqlite")
RAW_DIR = Path("data/raw/hkjc")


def connect(db_path: Path = STRUCTURED_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    init_schema(con)
    return con


def init_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS scrape_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            finished_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (race_date, racecourse)
        );

        CREATE INDEX IF NOT EXISTS idx_scrape_jobs_status
        ON scrape_jobs (status, race_date, racecourse);

        CREATE TABLE IF NOT EXISTS race_results (
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            place TEXT NOT NULL,
            horse_no TEXT,
            horse_name TEXT,
            horse_code TEXT,
            jockey TEXT,
            trainer TEXT,
            actual_weight TEXT,
            declared_horse_weight TEXT,
            draw TEXT,
            lbw TEXT,
            running_position TEXT,
            finish_time TEXT,
            win_odds TEXT,
            source_path TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (race_date, racecourse, race_no, place, horse_no)
        );

        CREATE TABLE IF NOT EXISTS dividends (
            race_date TEXT NOT NULL,
            racecourse TEXT,
            race_no INTEGER NOT NULL,
            pool TEXT NOT NULL,
            winning_combination TEXT NOT NULL,
            dividend TEXT NOT NULL,
            source_path TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (race_date, race_no, pool, winning_combination, dividend)
        );

        CREATE TABLE IF NOT EXISTS race_metadata (
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            race_index TEXT,
            race_class TEXT,
            distance_m INTEGER,
            rating_range TEXT,
            going TEXT,
            race_name TEXT,
            prize_money TEXT,
            course TEXT,
            surface TEXT,
            course_layout TEXT,
            time_text TEXT,
            sectional_time_text TEXT,
            source_path TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (race_date, racecourse, race_no)
        );

        CREATE TABLE IF NOT EXISTS race_entries (
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            horse_no TEXT NOT NULL,
            horse_name TEXT,
            horse_code TEXT,
            last_6_runs TEXT,
            actual_weight TEXT,
            jockey TEXT,
            draw TEXT,
            trainer TEXT,
            international_rating TEXT,
            rating TEXT,
            rating_change TEXT,
            declared_horse_weight TEXT,
            horse_weight_change TEXT,
            best_time TEXT,
            age TEXT,
            wfa TEXT,
            sex TEXT,
            season_stakes TEXT,
            priority TEXT,
            days_since_last_run TEXT,
            gear TEXT,
            owner TEXT,
            sire TEXT,
            dam TEXT,
            import_category TEXT,
            standby INTEGER NOT NULL DEFAULT 0,
            source_path TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (race_date, racecourse, race_no, horse_no, standby)
        );

        CREATE TABLE IF NOT EXISTS horse_profiles (
            horse_code TEXT PRIMARY KEY,
            horse_name TEXT,
            country TEXT,
            age TEXT,
            colour TEXT,
            sex TEXT,
            import_type TEXT,
            season_stakes TEXT,
            total_stakes TEXT,
            starts_summary TEXT,
            starts_past_10_meetings TEXT,
            current_location TEXT,
            import_date TEXT,
            trainer TEXT,
            owner TEXT,
            current_rating TEXT,
            start_of_season_rating TEXT,
            sire TEXT,
            dam TEXT,
            dam_sire TEXT,
            same_sire TEXT,
            source_path TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS horse_form_records (
            horse_code TEXT NOT NULL,
            race_index TEXT NOT NULL,
            place TEXT,
            race_date TEXT,
            racecourse TEXT,
            track TEXT,
            course TEXT,
            distance_m INTEGER,
            going TEXT,
            race_class TEXT,
            draw TEXT,
            rating TEXT,
            trainer TEXT,
            jockey TEXT,
            lbw TEXT,
            win_odds TEXT,
            actual_weight TEXT,
            running_position TEXT,
            finish_time TEXT,
            declared_horse_weight TEXT,
            gear TEXT,
            season TEXT,
            source_path TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (horse_code, race_index)
        );

        CREATE TABLE IF NOT EXISTS race_change_events (
            race_date TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            horse_no TEXT,
            horse_name TEXT,
            related_horse_name TEXT,
            jockey TEXT,
            declared_weight TEXT,
            event_time_text TEXT,
            description TEXT NOT NULL,
            source_path TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (race_date, race_no, sequence)
        );

        CREATE INDEX IF NOT EXISTS idx_race_results_horse_history
        ON race_results (horse_code, race_date DESC, racecourse DESC, race_no DESC);

        CREATE INDEX IF NOT EXISTS idx_race_results_jockey_date
        ON race_results (jockey, race_date);

        CREATE INDEX IF NOT EXISTS idx_race_results_trainer_date
        ON race_results (trainer, race_date);

        CREATE INDEX IF NOT EXISTS idx_race_results_race_runner
        ON race_results (race_date, racecourse, race_no, horse_no);

        CREATE INDEX IF NOT EXISTS idx_race_results_race_horse_code
        ON race_results (race_date, racecourse, race_no, horse_code);

        CREATE INDEX IF NOT EXISTS idx_race_metadata_distance
        ON race_metadata (distance_m, race_date, racecourse, race_no);

        CREATE INDEX IF NOT EXISTS idx_race_metadata_surface
        ON race_metadata (surface, race_date, racecourse, race_no);

        CREATE INDEX IF NOT EXISTS idx_horse_form_records_horse_date
        ON horse_form_records (horse_code, race_date DESC);
        """
    )
    con.commit()


def seed_jobs_from_legacy_odds(
    legacy_db: Path = Path("data/processed/legacy_horse_odds.sqlite"),
    db_path: Path = STRUCTURED_DB,
    racecourses: tuple[str, ...] = ("HV", "ST"),
) -> int:
    con = connect(db_path)
    legacy = sqlite3.connect(legacy_db)
    dates = [row[0] for row in legacy.execute("SELECT DISTINCT race_date FROM legacy_horse_odds ORDER BY race_date DESC")]
    inserted = 0
    for race_date in dates:
        for racecourse in racecourses:
            cur = con.execute(
                """
                INSERT OR IGNORE INTO scrape_jobs (race_date, racecourse)
                VALUES (?, ?)
                """,
                (race_date, racecourse),
            )
            inserted += cur.rowcount
    con.commit()
    legacy.close()
    con.close()
    return inserted


def next_pending_job(db_path: Path = STRUCTURED_DB) -> sqlite3.Row | None:
    con = connect(db_path)
    job = con.execute(
        """
        SELECT * FROM scrape_jobs
        WHERE status IN ('pending', 'failed')
        ORDER BY race_date DESC, racecourse ASC
        LIMIT 1
        """
    ).fetchone()
    con.close()
    return job


def mark_job(job_id: int, status: str, error: str | None = None, db_path: Path = STRUCTURED_DB) -> None:
    con = connect(db_path)
    now = now_text()
    if status == "running":
        con.execute(
            """
            UPDATE scrape_jobs
            SET status = ?, attempts = attempts + 1, started_at = ?, updated_at = ?, last_error = NULL
            WHERE id = ?
            """,
            (status, now, now, job_id),
        )
    else:
        con.execute(
            """
            UPDATE scrape_jobs
            SET status = ?, finished_at = ?, updated_at = ?, last_error = ?
            WHERE id = ?
            """,
            (status, now, now, error, job_id),
        )
    con.commit()
    con.close()


def parse_job_outputs(race_date: str, racecourse: str, max_race_no: int = 12, db_path: Path = STRUCTURED_DB) -> dict[str, int]:
    con = connect(db_path)
    result_count = 0
    dividend_count = 0
    entry_count = 0
    for race_no in range(1, max_race_no + 1):
        race_card = latest_parsed_json("race_cards", f"{race_date}_{racecourse}_R{race_no}")
        if race_card:
            entry_count += upsert_race_entries(con, race_date, racecourse, race_no, race_card)
        parsed = latest_parsed_json("results", f"{race_date}_{racecourse}_R{race_no}")
        if not parsed:
            continue
        upsert_race_metadata(con, race_date, racecourse, race_no, parsed)
        result_count += upsert_race_results(con, race_date, racecourse, race_no, parsed)
        dividend_count += upsert_dividends(con, race_date, racecourse, race_no, parsed)
        entry_count += upsert_race_entries_from_results(con, race_date, racecourse, race_no, parsed)
    con.commit()
    con.close()
    return {"race_results": result_count, "dividends": dividend_count, "race_entries": entry_count}


def parse_horse_history_outputs(db_path: Path = STRUCTURED_DB) -> dict[str, int]:
    con = connect(db_path)
    profile_count = 0
    form_count = 0
    for latest in (RAW_DIR / "horse_history").glob("*/latest.json"):
        parsed = latest_parsed_json("horse_history", latest.parent.name)
        if not parsed:
            continue
        profile_count += upsert_horse_profile(con, parsed)
        form_count += upsert_horse_form_records(con, parsed)
    con.commit()
    con.close()
    return {"horse_profiles": profile_count, "horse_form_records": form_count}


def parse_change_outputs(db_path: Path = STRUCTURED_DB) -> dict[str, int]:
    con = connect(db_path)
    event_count = 0
    seen_meeting_dates: set[str] = set()
    for latest in (RAW_DIR / "changes").glob("*/latest.json"):
        parsed = latest_parsed_json("changes", latest.parent.name)
        if not parsed:
            continue
        meeting_date = detect_change_meeting_date(parsed[1]) or latest.parent.name
        if meeting_date in seen_meeting_dates:
            continue
        seen_meeting_dates.add(meeting_date)
        event_count += upsert_race_change_events(con, latest.parent.name, parsed)
    con.commit()
    con.close()
    return {"race_change_events": event_count}


def upsert_race_metadata(
    con: sqlite3.Connection,
    race_date: str,
    racecourse: str,
    race_no: int,
    parsed: tuple[Path, dict[str, Any]],
) -> int:
    parsed_path, payload = parsed
    rows = find_race_info_table(payload)
    if not rows:
        return 0

    race_index = parse_race_index(rows[0][0]) if rows and rows[0] else None
    class_info = rows[1][0] if len(rows) > 1 and rows[1] else None
    race_class, distance_m, rating_range = parse_class_distance(class_info)
    going = rows[1][2] if len(rows) > 1 and len(rows[1]) >= 3 else None
    race_name = rows[2][0] if len(rows) > 2 and rows[2] else None
    course_text = rows[2][2] if len(rows) > 2 and len(rows[2]) >= 3 else None
    surface, course_layout = parse_course(course_text)
    prize_money = rows[3][0] if len(rows) > 3 and rows[3] else None
    time_text = " ".join(rows[3][2:]) if len(rows) > 3 and len(rows[3]) > 2 else None
    sectional_time_text = " | ".join(rows[4][1:]) if len(rows) > 4 and len(rows[4]) > 1 else None

    con.execute(
        """
        INSERT OR REPLACE INTO race_metadata (
            race_date, racecourse, race_no, race_index, race_class, distance_m,
            rating_range, going, race_name, prize_money, course, surface,
            course_layout, time_text, sectional_time_text, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            race_date,
            racecourse,
            race_no,
            race_index,
            race_class,
            distance_m,
            rating_range,
            going,
            race_name,
            prize_money,
            course_text,
            surface,
            course_layout,
            time_text,
            sectional_time_text,
            str(parsed_path),
            now_text(),
        ),
    )
    return 1


def upsert_race_results(
    con: sqlite3.Connection,
    race_date: str,
    racecourse: str,
    race_no: int,
    parsed: tuple[Path, dict[str, Any]],
) -> int:
    parsed_path, payload = parsed
    rows = find_table(payload, ["Pla.", "Horse No.", "Horse", "Jockey"])
    if not rows:
        return 0
    updated_at = now_text()
    count = 0
    for row in rows[1:]:
        if len(row) < 12 or not row[0].strip().isdigit():
            continue
        horse_name, horse_code = split_horse(row[2])
        con.execute(
            """
            INSERT OR REPLACE INTO race_results (
                race_date, racecourse, race_no, place, horse_no, horse_name, horse_code,
                jockey, trainer, actual_weight, declared_horse_weight, draw, lbw,
                running_position, finish_time, win_odds, source_path, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                race_date,
                racecourse,
                race_no,
                row[0],
                row[1],
                horse_name,
                horse_code,
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
                row[10],
                row[11],
                str(parsed_path),
                updated_at,
            ),
        )
        count += 1
    return count


def upsert_dividends(
    con: sqlite3.Connection,
    race_date: str,
    racecourse: str,
    race_no: int,
    parsed: tuple[Path, dict[str, Any]],
) -> int:
    parsed_path, payload = parsed
    rows = find_table(payload, ["Pool", "Winning Combination", "Dividend (HK$)"])
    if not rows:
        return 0
    updated_at = now_text()
    count = 0
    current_pool = ""
    for row in rows[2:]:
        if len(row) == 3:
            current_pool = row[0]
            combination = row[1]
            dividend = row[2]
        elif len(row) == 2 and current_pool:
            combination = row[0]
            dividend = row[1]
        else:
            continue
        con.execute(
            """
            INSERT OR REPLACE INTO dividends (
                race_date, racecourse, race_no, pool, winning_combination, dividend, source_path, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (race_date, racecourse, race_no, current_pool, combination, dividend, str(parsed_path), updated_at),
        )
        count += 1
    return count


ENTRY_COLUMNS = [
    "Horse No.",
    "Last 6 Runs",
    "Horse",
    "Brand No.",
    "Wt.",
    "Jockey",
    "Over Wt.",
    "Draw",
    "Trainer",
    "Int'l Rtg.",
    "Rtg.",
    "Rtg.+/-",
    "Horse Wt. (Declaration)",
    "Wt.+/- (vs Declaration)",
    "Best Time",
    "Age",
    "WFA",
    "Sex",
    "Season Stakes",
    "Priority",
    "Days since Last Run",
    "Gear",
    "Owner",
    "Sire",
    "Dam",
    "Import Cat.",
]


def upsert_race_entries(
    con: sqlite3.Connection,
    race_date: str,
    racecourse: str,
    race_no: int,
    parsed: tuple[Path, dict[str, Any]],
) -> int:
    parsed_path, payload = parsed
    count = 0
    for row, standby in iter_entry_rows(payload):
        count += upsert_race_entry_row(con, race_date, racecourse, race_no, row, standby, parsed_path)
    return count


def upsert_race_entries_from_results(
    con: sqlite3.Connection,
    race_date: str,
    racecourse: str,
    race_no: int,
    parsed: tuple[Path, dict[str, Any]],
) -> int:
    parsed_path, payload = parsed
    rows = find_table(payload, ["Pla.", "Horse No.", "Horse", "Jockey"])
    if not rows:
        return 0
    count = 0
    for row in rows[1:]:
        if len(row) < 8 or not row[0].strip().isdigit():
            continue
        horse_name, horse_code = split_horse(row[2])
        entry = {
            "horse_no": row[1],
            "horse_name": horse_name,
            "horse_code": horse_code,
            "actual_weight": row[5] if len(row) > 5 else None,
            "jockey": row[3] if len(row) > 3 else None,
            "trainer": row[4] if len(row) > 4 else None,
            "declared_horse_weight": row[6] if len(row) > 6 else None,
            "draw": row[7] if len(row) > 7 else None,
            "source_path": str(parsed_path),
        }
        upsert_entry_dict(con, race_date, racecourse, race_no, entry, standby=0)
        count += 1
    return count


def iter_entry_rows(payload: dict[str, Any]) -> list[tuple[dict[str, str | None], int]]:
    rows: list[tuple[dict[str, str | None], int]] = []
    for table in payload.get("tables", []):
        table_rows = table.get("rows", [])
        for header_index, header in enumerate(table_rows):
            if not is_entry_header(header):
                continue
            standby = 1 if any("Stand-by Starter" in " ".join(r) for r in table_rows[:header_index]) else 0
            for row in table_rows[header_index + 1 :]:
                if len(row) < 4 or not row[0].strip().isdigit():
                    continue
                values = normalize_entry_values(row)
                if values:
                    rows.append((values, standby))
            break
    return rows


def is_entry_header(row: list[str]) -> bool:
    return all(item in row for item in ["Horse No.", "Horse", "Jockey", "Trainer"]) and (
        "Last 6 Runs" in row or "Horse Wt. (Declaration)" in row
    )


def normalize_entry_values(row: list[str]) -> dict[str, str | None] | None:
    if len(row) == 10:
        return {
            "horse_no": clean(row[0]),
            "horse_name": clean(row[1]),
            "declared_horse_weight": clean(row[2]),
            "actual_weight": clean(row[3]),
            "rating": clean(row[4]),
            "age": clean(row[5]),
            "last_6_runs": clean(row[6]),
            "trainer": clean(row[7]),
            "priority": clean(row[8]),
            "gear": clean(row[9]),
        }
    if len(row) < len(ENTRY_COLUMNS):
        return None
    data = dict(zip(ENTRY_COLUMNS, row))
    return {
        "horse_no": clean(data.get("Horse No.")),
        "last_6_runs": clean(data.get("Last 6 Runs")),
        "horse_name": clean(data.get("Horse")),
        "horse_code": clean(data.get("Brand No.")),
        "actual_weight": clean(data.get("Wt.")),
        "jockey": clean(data.get("Jockey")),
        "draw": clean(data.get("Draw")),
        "trainer": clean(data.get("Trainer")),
        "international_rating": clean(data.get("Int'l Rtg.")),
        "rating": clean(data.get("Rtg.")),
        "rating_change": clean(data.get("Rtg.+/-")),
        "declared_horse_weight": clean(data.get("Horse Wt. (Declaration)")),
        "horse_weight_change": clean(data.get("Wt.+/- (vs Declaration)")),
        "best_time": clean(data.get("Best Time")),
        "age": clean(data.get("Age")),
        "wfa": clean(data.get("WFA")),
        "sex": clean(data.get("Sex")),
        "season_stakes": clean(data.get("Season Stakes")),
        "priority": clean(data.get("Priority")),
        "days_since_last_run": clean(data.get("Days since Last Run")),
        "gear": clean(data.get("Gear")),
        "owner": clean(data.get("Owner")),
        "sire": clean(data.get("Sire")),
        "dam": clean(data.get("Dam")),
        "import_category": clean(data.get("Import Cat.")),
    }


def upsert_race_entry_row(
    con: sqlite3.Connection,
    race_date: str,
    racecourse: str,
    race_no: int,
    row: dict[str, str | None],
    standby: int,
    source_path: Path,
) -> int:
    row["source_path"] = str(source_path)
    upsert_entry_dict(con, race_date, racecourse, race_no, row, standby)
    return 1


def upsert_entry_dict(
    con: sqlite3.Connection,
    race_date: str,
    racecourse: str,
    race_no: int,
    row: dict[str, str | None],
    standby: int,
) -> None:
    con.execute(
        """
        INSERT OR REPLACE INTO race_entries (
            race_date, racecourse, race_no, horse_no, horse_name, horse_code,
            last_6_runs, actual_weight, jockey, draw, trainer, international_rating,
            rating, rating_change, declared_horse_weight, horse_weight_change,
            best_time, age, wfa, sex, season_stakes, priority, days_since_last_run,
            gear, owner, sire, dam, import_category, standby, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            race_date,
            racecourse,
            race_no,
            row.get("horse_no"),
            row.get("horse_name"),
            row.get("horse_code"),
            row.get("last_6_runs"),
            row.get("actual_weight"),
            row.get("jockey"),
            row.get("draw"),
            row.get("trainer"),
            row.get("international_rating"),
            row.get("rating"),
            row.get("rating_change"),
            row.get("declared_horse_weight"),
            row.get("horse_weight_change"),
            row.get("best_time"),
            row.get("age"),
            row.get("wfa"),
            row.get("sex"),
            row.get("season_stakes"),
            row.get("priority"),
            row.get("days_since_last_run"),
            row.get("gear"),
            row.get("owner"),
            row.get("sire"),
            row.get("dam"),
            row.get("import_category"),
            standby,
            row.get("source_path") or "",
            now_text(),
        ),
    )


HORSE_FORM_HEADER = [
    "Race Index",
    "Pla.",
    "Date",
    "RC /Track/ Course",
    "Dist.",
    "G",
    "Race Class",
    "Dr.",
    "Rtg.",
    "Trainer",
    "Jockey",
    "LBW",
    "Win Odds",
    "Act. Wt.",
    "Running Position",
    "Finish Time",
    "Declar. Horse Wt.",
    "Gear",
]


def upsert_horse_profile(con: sqlite3.Connection, parsed: tuple[Path, dict[str, Any]]) -> int:
    parsed_path, payload = parsed
    title = horse_title(payload)
    if not title:
        return 0
    horse_name, horse_code = title
    values = horse_profile_values(payload)
    country, age = split_pair(values.get("Country of Origin / Age"))
    colour, sex = split_pair(values.get("Colour / Sex"))
    con.execute(
        """
        INSERT OR REPLACE INTO horse_profiles (
            horse_code, horse_name, country, age, colour, sex, import_type,
            season_stakes, total_stakes, starts_summary, starts_past_10_meetings,
            current_location, import_date, trainer, owner, current_rating,
            start_of_season_rating, sire, dam, dam_sire, same_sire, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            horse_code,
            horse_name,
            country,
            age,
            colour,
            sex,
            clean(values.get("Import Type")),
            clean(values.get("Season Stakes*")),
            clean(values.get("Total Stakes*")),
            clean(values.get("No. of 1-2-3-Starts*")),
            clean(values.get("No. of starts in past 10 race meetings")),
            clean(values.get("Current Location (Arrival Date)")),
            clean(values.get("Import Date")),
            clean(values.get("Trainer")),
            clean(values.get("Owner")),
            clean(values.get("Current Rating")),
            clean(values.get("Start of Season Rating")),
            clean(values.get("Sire")),
            clean(values.get("Dam")),
            clean(values.get("Dam's Sire")),
            clean(values.get("Same Sire")),
            str(parsed_path),
            now_text(),
        ),
    )
    return 1


def upsert_horse_form_records(con: sqlite3.Connection, parsed: tuple[Path, dict[str, Any]]) -> int:
    parsed_path, payload = parsed
    title = horse_title(payload)
    if not title:
        return 0
    _horse_name, horse_code = title
    rows = find_horse_form_table(payload)
    if not rows:
        return 0
    count = 0
    season: str | None = None
    for row in rows[1:]:
        if len(row) == 1 and "Season" in row[0]:
            season = row[0]
            continue
        if len(row) < len(HORSE_FORM_HEADER) or not row[0].strip().isdigit():
            continue
        values = dict(zip(HORSE_FORM_HEADER, row))
        racecourse, track, course = parse_rc_track_course(values.get("RC /Track/ Course"))
        con.execute(
            """
            INSERT OR REPLACE INTO horse_form_records (
                horse_code, race_index, place, race_date, racecourse, track, course,
                distance_m, going, race_class, draw, rating, trainer, jockey, lbw,
                win_odds, actual_weight, running_position, finish_time,
                declared_horse_weight, gear, season, source_path, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                horse_code,
                clean(values.get("Race Index")),
                clean(values.get("Pla.")),
                parse_hkjc_short_date(values.get("Date")),
                racecourse,
                track,
                course,
                parse_int_text(values.get("Dist.")),
                clean(values.get("G")),
                clean(values.get("Race Class")),
                clean(values.get("Dr.")),
                clean(values.get("Rtg.")),
                clean(values.get("Trainer")),
                clean(values.get("Jockey")),
                clean(values.get("LBW")),
                clean(values.get("Win Odds")),
                clean(values.get("Act. Wt.")),
                clean(values.get("Running Position")),
                clean(values.get("Finish Time")),
                clean(values.get("Declar. Horse Wt.")),
                clean(values.get("Gear")),
                season,
                str(parsed_path),
                now_text(),
            ),
        )
        count += 1
    return count


def upsert_race_change_events(
    con: sqlite3.Connection,
    race_date: str,
    parsed: tuple[Path, dict[str, Any]],
) -> int:
    parsed_path, payload = parsed
    rows = find_change_table(payload)
    if not rows:
        return 0
    race_date = detect_change_meeting_date(payload) or race_date
    con.execute("DELETE FROM race_change_events WHERE race_date = ?", (race_date,))
    count = 0
    for row in rows[1:]:
        if len(row) < 2:
            continue
        race_no = parse_race_no(row[0])
        description = clean(row[1])
        if race_no is None or not description or description == "--":
            continue
        for event in split_change_description(description):
            count += 1
            con.execute(
                """
                INSERT OR REPLACE INTO race_change_events (
                    race_date, race_no, sequence, event_type, horse_no, horse_name,
                    related_horse_name, jockey, declared_weight, event_time_text,
                    description, source_path, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    race_date,
                    race_no,
                    count,
                    event["event_type"],
                    event.get("horse_no"),
                    event.get("horse_name"),
                    event.get("related_horse_name"),
                    event.get("jockey"),
                    event.get("declared_weight"),
                    event.get("event_time_text"),
                    event["description"],
                    str(parsed_path),
                    now_text(),
                ),
            )
    return count


def find_change_table(payload: dict[str, Any]) -> list[list[str]] | None:
    for table in payload.get("tables", []):
        rows = table.get("rows", [])
        if rows and rows[0] == ["Race", "Description"]:
            return rows
    return None


def detect_change_meeting_date(payload: dict[str, Any]) -> str | None:
    for text in payload.get("text_blocks", []):
        match = re.search(r"(\d{2})/(\d{2})/(\d{4})\s+(Sha Tin|Happy Valley)", text)
        if match:
            day, month, year, _course = match.groups()
            return f"{year}-{month}-{day}"
    return None


def split_change_description(description: str) -> list[dict[str, str | None]]:
    event_texts = re.findall(r".*?\(\d{2}/\d{2}\s+\d{2}:\d{2}\)", description)
    if not event_texts:
        event_texts = [description]
    return [parse_change_event(text.strip()) for text in event_texts if text.strip()]


def parse_change_event(text: str) -> dict[str, str | None]:
    event: dict[str, str | None] = {
        "event_type": "other",
        "description": text,
        "event_time_text": None,
    }
    time_match = re.search(r"\((\d{2}/\d{2}\s+\d{2}:\d{2})\)$", text)
    if time_match:
        event["event_time_text"] = time_match.group(1)
    scratch = re.search(r"Horse\s+(\d+)\s*,\s*(.*?)\s+Scratched\.", text, flags=re.IGNORECASE)
    if scratch:
        event.update({"event_type": "scratched", "horse_no": scratch.group(1), "horse_name": clean(scratch.group(2))})
    promoted = re.search(r"Standby starter\s+(.*?)\s+Promoted\.", text, flags=re.IGNORECASE)
    if promoted:
        event.update({"event_type": "standby_promoted", "related_horse_name": clean(promoted.group(1))})
    jockey = re.search(r"Horse\s+(\d+)\s+(.*?)\s+will be ridden by\s+(.*?)\s*\.", text, flags=re.IGNORECASE)
    if jockey:
        event.update(
            {
                "event_type": "jockey_change",
                "horse_no": jockey.group(1),
                "horse_name": clean(jockey.group(2)),
                "jockey": clean(jockey.group(3)),
            }
        )
    weight = re.search(r"Horse\s+(\d+)\s+(.*?)\s+will carry\s+(\d+)\s+lbs\.", text, flags=re.IGNORECASE)
    if weight:
        event.update(
            {
                "event_type": "weight_change",
                "horse_no": weight.group(1),
                "horse_name": clean(weight.group(2)),
                "declared_weight": weight.group(3),
            }
        )
    return event


def parse_race_no(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"Race\s+(\d+)", value, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def horse_title(payload: dict[str, Any]) -> tuple[str, str] | None:
    for table in payload.get("tables", []):
        for row in table.get("rows", [])[:3]:
            if not row:
                continue
            match = re.match(r"^(.+?)\s+\(([A-Z]\d{3})\)$", row[0].strip())
            if match:
                return match.group(1).strip(), match.group(2)
    return None


def horse_profile_values(payload: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    labels = {
        "Country of Origin / Age",
        "Colour / Sex",
        "Import Type",
        "Season Stakes*",
        "Total Stakes*",
        "No. of 1-2-3-Starts*",
        "No. of starts in past 10 race meetings",
        "Current Location (Arrival Date)",
        "Import Date",
        "Trainer",
        "Owner",
        "Current Rating",
        "Start of Season Rating",
        "Sire",
        "Dam",
        "Dam's Sire",
        "Same Sire",
    }
    for table in payload.get("tables", []):
        for row in table.get("rows", []):
            if len(row) >= 3 and row[0] in labels:
                values[row[0]] = row[2]
    return values


def find_horse_form_table(payload: dict[str, Any]) -> list[list[str]] | None:
    for table in payload.get("tables", []):
        rows = table.get("rows", [])
        if rows and all(item in rows[0] for item in ["Race Index", "Pla.", "Date", "Win Odds"]):
            return rows
    return None


def split_pair(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    parts = [clean(part) for part in value.split("/", 1)]
    return (parts[0], parts[1] if len(parts) > 1 else None)


def parse_rc_track_course(value: str | None) -> tuple[str | None, str | None, str | None]:
    if not value:
        return None, None, None
    parts = [clean(part) for part in value.split("/")]
    return (
        parts[0] if len(parts) > 0 else None,
        parts[1] if len(parts) > 1 else None,
        parts[2] if len(parts) > 2 else None,
    )


def parse_hkjc_short_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.match(r"^(\d{2})/(\d{2})/(\d{2})$", value.strip())
    if not match:
        return clean(value)
    day, month, year = match.groups()
    return f"20{year}-{month}-{day}"


def parse_int_text(value: Any) -> int | None:
    text = clean(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def latest_parsed_json(kind: str, identity: str) -> tuple[Path, dict[str, Any]] | None:
    latest = RAW_DIR / kind / identity / "latest.json"
    if not latest.exists():
        return None
    meta = json.loads(latest.read_text(encoding="utf-8"))
    parsed_path = Path(meta["parsed_json_path"])
    if not parsed_path.exists():
        return None
    return parsed_path, json.loads(parsed_path.read_text(encoding="utf-8"))


def find_table(payload: dict[str, Any], header: list[str]) -> list[list[str]] | None:
    for table in payload.get("tables", []):
        rows = table.get("rows", [])
        if not rows:
            continue
        for row in rows[:3]:
            if all(item in row for item in header):
                return rows
    return None


def find_race_info_table(payload: dict[str, Any]) -> list[list[str]] | None:
    for table in payload.get("tables", []):
        rows = table.get("rows", [])
        if len(rows) >= 4 and rows[0] and re.match(r"^RACE\s+\d+\s+\(\d+\)", rows[0][0]):
            return rows
    return None


def parse_race_index(value: str) -> str | None:
    match = re.search(r"\((\d+)\)", value)
    return match.group(1) if match else None


def parse_class_distance(value: str | None) -> tuple[str | None, int | None, str | None]:
    if not value:
        return None, None, None
    normalized = " ".join(value.split())
    distance_match = re.search(r"(\d{3,4})M", normalized)
    rating_match = re.search(r"\(([^)]+)\)", normalized)
    race_class = normalized
    if distance_match:
        race_class = race_class[: distance_match.start()].strip(" -")
    return (
        race_class or None,
        int(distance_match.group(1)) if distance_match else None,
        rating_match.group(1) if rating_match else None,
    )


def parse_course(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    surface = value.split("-", 1)[0].strip()
    layout_match = re.search(r'"([^"]+)"', value)
    return surface or None, layout_match.group(1) if layout_match else None


def split_horse(value: str) -> tuple[str, str | None]:
    match = re.match(r"^(.*?)\s*\(([A-Z]\d+)\)$", value.strip())
    if not match:
        return value.strip(), None
    return match.group(1).strip(), match.group(2)


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return None if text in {"", "-"} else text


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
