import sqlite3
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parents[2]))

from scripts.audit_legacy_odds import audit_legacy_odds


def test_audit_legacy_odds_detects_duplicate_snapshots(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_odds.sqlite"
    con = sqlite3.connect(db_path)
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
            source TEXT NOT NULL DEFAULT 'digit-ai.horse_odds'
        );
        """
    )
    con.executemany(
        """
        INSERT INTO legacy_horse_odds (
            legacy_id, race_date, race_no, odds_type, odds_value, odds,
            implied_probability, snapshot_at, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("1", "2026-05-20", 3, "win", "1", 11.0, 0.090909, "2026-05-20T19:29:32", "hkjc"),
            ("2", "2026-05-20", 3, "win", "1", 11.0, 0.090909, "2026-05-20T19:29:32", "hkjc"),
            ("3", "2026-05-20", 3, "win", "2", 5.0, 0.2, "2026-05-20T19:29:32", "hkjc"),
        ],
    )
    con.commit()
    con.close()

    report = audit_legacy_odds(db_path)

    assert report["tableExists"] is True
    assert report["snapshotCount"] == 3
    assert report["raceCount"] == 1
    assert report["dateRange"] == {"minDate": "2026-05-20", "maxDate": "2026-05-20"}
    assert report["missingOddsTypes"] == ["fct", "qin", "qpl"]
    assert report["duplicateGroupCount"] == 1
    assert report["duplicateSnapshotCount"] == 1
    assert report["duplicateGroups"][0]["oddsValue"] == "1"
    assert report["criticalMissing"]["snapshot_at"] == 0
    assert report["anomalyCounts"]["invalid_odds"] == 0


def test_audit_legacy_odds_handles_missing_table(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.sqlite"
    sqlite3.connect(db_path).close()

    report = audit_legacy_odds(db_path)

    assert report["tableExists"] is False
    assert report["snapshotCount"] == 0
    assert report["duplicateGroupCount"] == 0
