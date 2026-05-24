import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_runner_features_api(tmp_path: Path) -> None:
    db_path = tmp_path / "features_api.sqlite"
    build_db(db_path)
    original_path = settings.hkjc_structured_db_path
    settings.hkjc_structured_db_path = str(db_path)
    client = TestClient(app)

    try:
        response = client.get("/api/v1/features/runner-features?race_date=2026-05-20&racecourse=HV&race_no=1")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["horse_code"] == "K099"
        assert item["implied_win_probability"] is None

        result_odds_response = client.get(
            "/api/v1/features/runner-features?race_date=2026-05-20&racecourse=HV&race_no=1&odds_mode=result_final"
        )
        assert result_odds_response.status_code == 200
        assert result_odds_response.json()["items"][0]["implied_win_probability"] == 0.5
    finally:
        settings.hkjc_structured_db_path = original_path


def build_db(path: Path) -> None:
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
        """
    )
    con.execute(
        """
        INSERT INTO race_results (
            race_date, racecourse, race_no, place, horse_no, horse_name, horse_code,
            jockey, trainer, actual_weight, declared_horse_weight, draw, lbw,
            running_position, finish_time, win_odds, source_path, updated_at
        )
        VALUES ('2026-05-20', 'HV', 1, '1', '7', 'KING ALLOY', 'K099',
                'A Jockey', 'A Trainer', '128', '1178', '1', '---',
                '1', '0:56.88', '2.0', 'sample', '2026-05-23T00:00:00')
        """
    )
    con.execute(
        """
        INSERT INTO race_metadata (
            race_date, racecourse, race_no, race_class, distance_m, going,
            race_name, surface, course_layout, source_path, updated_at
        )
        VALUES ('2026-05-20', 'HV', 1, 'Class 5', 1000, 'GOOD',
                'CELOSIA HANDICAP', 'TURF', 'A', 'sample', '2026-05-23T00:00:00')
        """
    )
    con.commit()
    con.close()
