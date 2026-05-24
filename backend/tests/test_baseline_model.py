import sqlite3
from pathlib import Path

from app.quant.models.baseline import predict_with_artifact, train_baseline_models, load_artifact


def test_train_and_predict_baseline_model(tmp_path: Path) -> None:
    db_path = tmp_path / "model.sqlite"
    artifact_dir = tmp_path / "models"
    build_model_db(db_path)

    result = train_baseline_models(db_path, artifact_dir=artifact_dir)

    assert result.row_count == 24
    assert Path(result.artifact_path).exists()
    artifact = load_artifact(Path(result.artifact_path))
    assert artifact["model_name"] == "baseline-logistic-no_odds"
    assert "implied_win_probability" not in artifact["feature_columns"]


def build_model_db(path: Path) -> None:
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
    records = []
    metadata = []
    for race_index in range(1, 5):
        race_date = f"2026-05-{race_index:02d}"
        metadata.append((race_date, "HV", 1, "Class 5", 1000, "GOOD", "TURF"))
        for horse_no in range(1, 7):
            place = str(horse_no)
            records.append(
                (
                    race_date,
                    "HV",
                    1,
                    place,
                    str(horse_no),
                    f"HORSE {horse_no}",
                    f"K{horse_no:03d}",
                    "A Jockey",
                    "A Trainer",
                    "128",
                    "1100",
                    str(horse_no),
                    "---" if horse_no == 1 else "1",
                    str(horse_no),
                    "1:00.00",
                    str(2 + horse_no),
                    "sample",
                    "2026-05-23T00:00:00",
                )
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
        records,
    )
    con.executemany(
        """
        INSERT INTO race_metadata (
            race_date, racecourse, race_no, race_class, distance_m, going, surface,
            source_path, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'sample', '2026-05-23T00:00:00')
        """,
        metadata,
    )
    con.commit()
    con.close()
