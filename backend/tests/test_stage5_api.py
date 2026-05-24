import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_odds_prediction_and_backtest_apis(tmp_path: Path) -> None:
    odds_db = tmp_path / "legacy_odds.sqlite"
    structured_db = tmp_path / "structured.sqlite"
    build_odds_db(odds_db)

    original_odds_path = settings.legacy_odds_db_path
    original_structured_path = settings.hkjc_structured_db_path
    settings.legacy_odds_db_path = str(odds_db)
    settings.hkjc_structured_db_path = str(structured_db)
    client = TestClient(app)

    try:
        import_status = client.post("/api/v1/odds/import-legacy")
        assert import_status.status_code == 200
        assert import_status.json()["summary"]["snapshotCount"] == 2

        snapshots = client.get("/api/v1/odds/snapshots?race_date=2026-05-20&race_no=3&odds_type=win")
        assert snapshots.status_code == 200
        assert snapshots.json()["items"][0]["oddsValue"] == "7"

        summary = client.get("/api/v1/odds/summary?race_date=2026-05-20")
        assert summary.status_code == 200
        assert summary.json()["items"][0]["snapshotCount"] == 2

        changes = client.get("/api/v1/odds/changes?race_date=2026-05-20&race_no=3&odds_type=win")
        assert changes.status_code == 200
        assert changes.json()["items"][0]["oddsValue"] == "7"
        assert changes.json()["items"][0]["points"][0]["odds"] == 2.6

        predictions = client.get("/api/v1/predictions?race_date=2026-05-20&racecourse=HV&race_no=1")
        assert predictions.status_code == 200
        assert predictions.json() == {"items": []}

        created = client.post(
            "/api/v1/backtests",
            json={"name": "smoke", "strategyName": "flat-win", "parameters": {"stake": 10}},
        )
        assert created.status_code == 200
        run_id = created.json()["id"]

        fetched = client.get(f"/api/v1/backtests/{run_id}")
        assert fetched.status_code == 200
        assert fetched.json()["parameters"] == {"stake": 10}

        results = client.get(f"/api/v1/backtests/{run_id}/results")
        assert results.status_code == 200
        assert results.json()["bets"] == []
    finally:
        settings.legacy_odds_db_path = original_odds_path
        settings.hkjc_structured_db_path = original_structured_path


def build_odds_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE legacy_horse_odds (
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
            source TEXT NOT NULL DEFAULT 'test'
        );
        """
    )
    con.executemany(
        """
        INSERT INTO legacy_horse_odds (
            legacy_id, race_date, race_no, odds_type, odds_value, odds,
            implied_probability, snapshot_at, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("1", "2026-05-20", 3, "win", "7", 2.6, 0.3846, "2026-05-20T12:00:00", "test"),
            ("2", "2026-05-20", 3, "win", "8", 4.8, 0.2083, "2026-05-20T12:01:00", "test"),
        ],
    )
    con.commit()
    con.close()
