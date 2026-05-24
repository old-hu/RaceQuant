import argparse
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.quant.features.engine import FeatureEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="构建赛马 runner 级别量化特征。")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--race-date")
    parser.add_argument("--racecourse")
    parser.add_argument("--race-no", type=int)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--odds-mode", choices=["none", "pre_start_latest", "result_final"], default="none")
    parser.add_argument("--odds-db", type=Path, default=Path("data/processed/legacy_horse_odds.sqlite"))
    parser.add_argument("--output", type=Path, default=Path("data/features/runner_features.json"))
    parser.add_argument("--write-db", action="store_true", help="写入 structured SQLite 的 runner_features 表。")
    args = parser.parse_args()

    features = FeatureEngine(args.db, odds_mode=args.odds_mode, odds_db_path=args.odds_db).build_runner_features(
        race_date=args.race_date,
        racecourse=args.racecourse,
        race_no=args.race_no,
        limit=args.limit,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps([asdict(row) for row in features], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if args.write_db:
        write_features(args.db, features)
    print(f"Wrote {len(features)} runner features to {args.output}")


def write_features(db_path: Path, features) -> None:
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS runner_features (
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            horse_code TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (race_date, racecourse, race_no, horse_code)
        );
        """
    )
    rows = [
        (
            row.race_date,
            row.racecourse,
            row.race_no,
            row.horse_code,
            json.dumps(asdict(row), ensure_ascii=False, sort_keys=True),
        )
        for row in features
    ]
    con.executemany(
        """
        INSERT OR REPLACE INTO runner_features (
            race_date, racecourse, race_no, horse_code, payload_json
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
