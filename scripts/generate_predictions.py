import argparse
import json
import sqlite3
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.quant.features.engine import FeatureEngine
from app.quant.models.baseline import load_artifact, predict_with_artifact


def main() -> None:
    parser = argparse.ArgumentParser(description="使用 baseline 模型生成预测和 value betting 信号。")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--race-date")
    parser.add_argument("--racecourse")
    parser.add_argument("--race-no", type=int)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--odds-db", type=Path, default=Path("data/processed/legacy_horse_odds.sqlite"))
    parser.add_argument("--output", type=Path, default=Path("frontend/public/data/baseline_predictions.json"))
    parser.add_argument("--write-db", action="store_true")
    parser.add_argument("--allow-result-final", action="store_true", help="Allow result_final odds mode for leakage/control experiments.")
    args = parser.parse_args()

    artifact = load_artifact(args.artifact)
    if artifact.get("odds_mode") == "result_final" and not args.allow_result_final:
        parser.error("The artifact uses result_final odds and requires --allow-result-final.")
    rows = FeatureEngine(
        args.db,
        odds_mode=artifact.get("odds_mode", "none"),
        odds_db_path=args.odds_db,
    ).build_runner_features(
        race_date=args.race_date,
        racecourse=args.racecourse,
        race_no=args.race_no,
        limit=args.limit,
    )
    predictions = predict_with_artifact(artifact, rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(predictions, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_db:
        write_predictions(args.db, predictions)
    print(f"Wrote {len(predictions)} predictions to {args.output}")


def write_predictions(db_path: Path, predictions: list[dict]) -> None:
    con = sqlite3.connect(db_path)
    con.executescript(
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
        );
        """
    )
    con.executemany(
        """
        INSERT OR REPLACE INTO model_predictions (
            race_date, racecourse, race_no, horse_code, model_name, model_version, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item["raceDate"],
                item["racecourse"],
                item["raceNo"],
                item["horseCode"],
                item["modelName"],
                item["modelVersion"],
                json.dumps(item, ensure_ascii=False, sort_keys=True),
            )
            for item in predictions
        ],
    )
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
