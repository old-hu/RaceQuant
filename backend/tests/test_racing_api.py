import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_racing_api_reads_structured_hkjc_data(tmp_path: Path) -> None:
    db_path = tmp_path / "hkjc_structured.sqlite"
    build_test_db(db_path)
    original_path = settings.hkjc_structured_db_path
    settings.hkjc_structured_db_path = str(db_path)
    client = TestClient(app)

    try:
        races = client.get("/api/v1/racing/races")
        assert races.status_code == 200
        assert races.json()["items"][0]["raceDate"] == "2026-05-20"
        assert races.json()["items"][0]["runnerCount"] == 2
        assert races.json()["items"][0]["distanceM"] == 1000

        race = client.get("/api/v1/racing/races/2026-05-20/HV/1")
        assert race.status_code == 200
        assert race.json()["raceClass"] == "Class 5"
        assert race.json()["going"] == "GOOD"
        assert race.json()["dividends"][0]["pool"] == "WIN"
        assert race.json()["entries"][0]["rating"] == "40"

        runners = client.get("/api/v1/racing/races/2026-05-20/HV/1/runners")
        assert runners.status_code == 200
        assert runners.json()["items"][0]["horseCode"] == "K099"

        entries = client.get("/api/v1/racing/races/2026-05-20/HV/1/entries")
        assert entries.status_code == 200
        assert entries.json()["items"][0]["horseName"] == "KING ALLOY"

        changes = client.get("/api/v1/racing/changes?race_date=2026-05-20&race_no=1")
        assert changes.status_code == 200
        assert changes.json()["items"][0]["eventType"] == "jockey_change"

        horse = client.get("/api/v1/racing/horses/K099")
        assert horse.status_code == 200
        assert horse.json()["horseName"] == "KING ALLOY"
        assert horse.json()["wins"] == 1

        history = client.get("/api/v1/racing/horses/K099/history")
        assert history.status_code == 200
        assert history.json()["items"][0]["raceIndex"] == "705"
        assert history.json()["items"][0]["distanceM"] == 1000
    finally:
        settings.hkjc_structured_db_path = original_path


def build_test_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE race_results (
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
        CREATE TABLE dividends (
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
        CREATE TABLE race_metadata (
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
        CREATE TABLE race_entries (
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
        CREATE TABLE horse_form_records (
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
        CREATE TABLE race_change_events (
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
        """
    )
    con.executemany(
        """
        INSERT INTO race_results (
            race_date, racecourse, race_no, place, horse_no, horse_name, horse_code,
            jockey, trainer, actual_weight, declared_horse_weight, draw, lbw,
            running_position, finish_time, win_odds, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "2026-05-20",
                "HV",
                1,
                "1",
                "7",
                "KING ALLOY",
                "K099",
                "R Kingscote",
                "K H Ting",
                "128",
                "1178",
                "1",
                "---",
                "2 2 1",
                "0:56.88",
                "2.6",
                "sample.json",
                "2026-05-23T09:00:00+08:00",
            ),
            (
                "2026-05-20",
                "HV",
                1,
                "2",
                "8",
                "SPICY SPANGLE",
                "J087",
                "H Bowman",
                "W K Mo",
                "128",
                "1109",
                "8",
                "1-3/4",
                "1 1 2",
                "0:57.15",
                "4.8",
                "sample.json",
                "2026-05-23T09:00:00+08:00",
            ),
        ],
    )
    con.execute(
        """
        INSERT INTO race_metadata (
            race_date, racecourse, race_no, race_index, race_class, distance_m,
            rating_range, going, race_name, prize_money, course, surface,
            course_layout, time_text, sectional_time_text, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "2026-05-20",
            "HV",
            1,
            "705",
            "Class 5",
            1000,
            "40-0",
            "GOOD",
            "CELOSIA HANDICAP",
            "HK$ 875,000",
            'TURF - "A" Course',
            "TURF",
            "A",
            "(56.88)",
            "12.65 | 20.95",
            "sample.json",
            "2026-05-23T09:00:00+08:00",
        ),
    )
    con.execute(
        """
        INSERT INTO dividends (
            race_date, racecourse, race_no, pool, winning_combination, dividend, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("2026-05-20", "HV", 1, "WIN", "7", "26.00", "sample.json", "2026-05-23T09:00:00+08:00"),
    )
    con.execute(
        """
        INSERT INTO race_entries (
            race_date, racecourse, race_no, horse_no, horse_name, horse_code,
            last_6_runs, actual_weight, jockey, draw, trainer, rating,
            declared_horse_weight, days_since_last_run, gear, standby, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "2026-05-20",
            "HV",
            1,
            "7",
            "KING ALLOY",
            "K099",
            "1/3/5/1/2/7",
            "128",
            "R Kingscote",
            "1",
            "K H Ting",
            "40",
            "1178",
            "17",
            "B/TT",
            0,
            "sample.json",
            "2026-05-23T09:00:00+08:00",
        ),
    )
    con.execute(
        """
        INSERT INTO horse_form_records (
            horse_code, race_index, place, race_date, racecourse, track, course,
            distance_m, going, race_class, draw, rating, trainer, jockey, lbw,
            win_odds, actual_weight, running_position, finish_time,
            declared_horse_weight, gear, season, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "K099",
            "705",
            "01",
            "2026-05-20",
            "HV",
            "Turf",
            '"A"',
            1000,
            "G",
            "5",
            "1",
            "33",
            "K H Ting",
            "R Kingscote",
            "1-3/4",
            "2.6",
            "128",
            "2 2 1",
            "0.56.88",
            "1178",
            "B",
            "25/26 Season",
            "sample.json",
            "2026-05-23T09:00:00+08:00",
        ),
    )
    con.execute(
        """
        INSERT INTO race_change_events (
            race_date, race_no, sequence, event_type, horse_no, horse_name,
            jockey, event_time_text, description, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "2026-05-20",
            1,
            1,
            "jockey_change",
            "7",
            "KING ALLOY",
            "R Kingscote",
            "20/05 12:00",
            "Horse 7 KING ALLOY will be ridden by R Kingscote.",
            "sample.json",
            "2026-05-23T09:00:00+08:00",
        ),
    )
    con.commit()
    con.close()
