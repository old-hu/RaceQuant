import sqlite3
from pathlib import Path

from app.quant.features.engine import FeatureEngine


def test_runner_features_use_prior_history_only(tmp_path: Path) -> None:
    db_path = tmp_path / "features.sqlite"
    build_feature_db(db_path)

    rows = FeatureEngine(db_path, odds_mode="result_final").build_runner_features(
        race_date="2026-05-20",
        racecourse="HV",
        race_no=1,
    )

    feature = next(row for row in rows if row.horse_code == "K099")
    assert feature.recent_3_starts == 3
    assert feature.recent_3_win_rate == 1 / 3
    assert feature.recent_3_place_rate == 2 / 3
    assert feature.days_since_last_run == 17
    assert feature.draw_bucket == "inside"
    assert feature.actual_weight_lbs == 128
    assert feature.declared_horse_weight_lbs == 1178
    assert feature.implied_win_probability == 0.5
    assert feature.distance_m == 1000
    assert feature.distance_starts == 2
    assert feature.distance_win_rate == 0.5
    assert feature.surface == "TURF"
    assert feature.surface_starts == 3
    assert feature.surface_win_rate == 1 / 3
    assert feature.class_change == "down"
    assert feature.jockey_win_rate == 1 / 3
    assert feature.trainer_win_rate == 1 / 3

    no_odds_rows = FeatureEngine(db_path, odds_mode="none").build_runner_features(
        race_date="2026-05-20",
        racecourse="HV",
        race_no=1,
    )
    no_odds_feature = next(row for row in no_odds_rows if row.horse_code == "K099")
    assert no_odds_feature.win_odds is None
    assert no_odds_feature.implied_win_probability is None

    cutoff_rows = FeatureEngine(db_path, odds_mode="pre_start_latest", odds_db_path=db_path).build_runner_features(
        race_date="2026-05-20",
        racecourse="HV",
        race_no=1,
    )
    cutoff_feature = next(row for row in cutoff_rows if row.horse_code == "K099")
    assert cutoff_feature.win_odds == 3.0
    assert cutoff_feature.implied_win_probability == 1 / 3


def build_feature_db(path: Path) -> None:
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
        CREATE TABLE legacy_horse_odds (
            legacy_id TEXT PRIMARY KEY,
            race_date TEXT,
            race_no INTEGER,
            odds_type TEXT NOT NULL,
            odds_value TEXT NOT NULL,
            odds REAL NOT NULL,
            snapshot_at TEXT
        );
        """
    )
    rows = [
        ("2026-05-20", "HV", 1, "1", "7", "KING ALLOY", "K099", "A Jockey", "A Trainer", "128", "1178", "1", "---", "1", "0:56.88", "2.0"),
        ("2026-05-03", "ST", 1, "3", "7", "KING ALLOY", "K099", "A Jockey", "A Trainer", "128", "1178", "8", "2", "3", "1:09.71", "14"),
        ("2026-04-15", "HV", 1, "1", "7", "KING ALLOY", "K099", "A Jockey", "A Trainer", "128", "1178", "12", "---", "1", "0:56.95", "5.5"),
        ("2026-04-01", "ST", 1, "5", "7", "KING ALLOY", "K099", "A Jockey", "A Trainer", "128", "1178", "4", "3", "5", "1:10.00", "8"),
    ]
    con.executemany(
        """
        INSERT INTO race_results (
            race_date, racecourse, race_no, place, horse_no, horse_name, horse_code,
            jockey, trainer, actual_weight, declared_horse_weight, draw, lbw,
            running_position, finish_time, win_odds, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'sample', '2026-05-23T00:00:00')
        """,
        rows,
    )
    con.executemany(
        """
        INSERT INTO legacy_horse_odds (
            legacy_id, race_date, race_no, odds_type, odds_value, odds, snapshot_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("odds-1", "2026-05-20", 1, "win", "7", 4.0, "2026-05-20T12:00:00"),
            ("odds-2", "2026-05-20", 1, "win", "7", 3.0, "2026-05-20T12:01:00"),
            ("odds-3", "2026-05-20", 1, "win", "7", 2.0, "2026-05-20T12:02:00"),
        ],
    )
    con.executemany(
        """
        INSERT INTO race_metadata (
            race_date, racecourse, race_no, race_class, distance_m, going,
            race_name, surface, course_layout, source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'sample', '2026-05-23T00:00:00')
        """,
        [
            ("2026-05-20", "HV", 1, "Class 5", 1000, "GOOD", "TODAY", "TURF", "A"),
            ("2026-05-03", "ST", 1, "Class 4", 1200, "GOOD", "PREV 1", "TURF", "B"),
            ("2026-04-15", "HV", 1, "Class 5", 1000, "GOOD", "PREV 2", "TURF", "A"),
            ("2026-04-01", "ST", 1, "Class 5", 1000, "GOOD", "PREV 3", "TURF", "C"),
        ],
    )
    con.commit()
    con.close()
