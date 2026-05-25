from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "backend"))

from app.quant.backtesting.engine import BacktestConfig, result_to_dict, run_backtest_from_db  # noqa: E402
from app.quant.features.engine import FeatureEngine  # noqa: E402
from app.quant.models.baseline import FEATURE_VERSION, TRAINING_DATASET_VERSION, load_artifact, predict_with_artifact, train_baseline_models  # noqa: E402


ODDS_MODES = ("none", "pre_start_latest", "result_final")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare baseline model lines across odds modes.")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--odds-db", type=Path, default=Path("data/processed/legacy_horse_odds.sqlite"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("models/baseline_comparison"))
    parser.add_argument("--output", type=Path, default=Path("data/reports/model_line_comparison.json"))
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--data-build-report", type=Path, default=Path("data/reports/local_data_build.json"))
    parser.add_argument("--min-edge", type=float, default=0.03)
    parser.add_argument("--top-n-per-race", type=int, default=1)
    args = parser.parse_args()

    data_build_id = data_build_id_from_report(args.data_build_report)
    rows = [
        compare_mode(
            odds_mode=mode,
            db_path=args.db,
            odds_db_path=args.odds_db,
            artifact_dir=args.artifact_dir,
            limit=args.limit,
            data_build_id=data_build_id,
            min_edge=args.min_edge,
            top_n_per_race=args.top_n_per_race,
        )
        for mode in ODDS_MODES
    ]
    report = {
        "dataBuildId": data_build_id,
        "trainingDatasetVersion": TRAINING_DATASET_VERSION,
        "featureVersion": FEATURE_VERSION,
        "modelLines": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary(report), ensure_ascii=False, indent=2))
    print(f"Wrote model line comparison to {args.output}")


def compare_mode(
    odds_mode: str,
    db_path: Path,
    odds_db_path: Path,
    artifact_dir: Path,
    limit: int,
    data_build_id: str | None,
    min_edge: float,
    top_n_per_race: int,
) -> dict[str, Any]:
    training = train_baseline_models(
        db_path,
        artifact_dir=artifact_dir,
        limit=limit,
        odds_mode=odds_mode,
        odds_db_path=odds_db_path,
        data_build_id=data_build_id,
    )
    artifact = load_artifact(Path(training.artifact_path))
    feature_rows = FeatureEngine(db_path, odds_mode=odds_mode, odds_db_path=odds_db_path).build_runner_features(limit=limit)
    predictions = predict_with_artifact(artifact, feature_rows)
    write_predictions(db_path, predictions)
    backtest = result_to_dict(
        run_backtest_from_db(
            db_path,
            BacktestConfig(
                bet_type="win",
                stake_strategy="flat",
                model_name=training.model_name,
                model_version=training.model_version,
                min_edge=min_edge,
                top_n_per_race=top_n_per_race,
                training_dataset_version=training.training_dataset_version,
                feature_version=training.feature_version,
                odds_mode=odds_mode,
                data_build_id=data_build_id,
            ),
        )
    )
    return {
        "oddsMode": odds_mode,
        "modelName": training.model_name,
        "modelVersion": training.model_version,
        "artifactPath": training.artifact_path,
        "metadataPath": training.metadata_path,
        "trainingRows": training.row_count,
        "trainingMetrics": training.metrics,
        "predictionCount": len(predictions),
        "backtestMetrics": backtest["metrics"],
    }


def write_predictions(db_path: Path, predictions: list[dict[str, Any]]) -> None:
    con = sqlite3.connect(db_path)
    try:
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
    finally:
        con.close()


def data_build_id_from_report(path: Path) -> str | None:
    if not path.exists():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    generated_at = report.get("generatedAt")
    source = report.get("source")
    return f"{source}:{generated_at}" if generated_at and source else generated_at


def summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataBuildId": report["dataBuildId"],
        "modelLines": [
            {
                "oddsMode": row["oddsMode"],
                "winAuc": row["trainingMetrics"].get("win_auc"),
                "winLogLoss": row["trainingMetrics"].get("win_log_loss"),
                "winBrier": row["trainingMetrics"].get("win_brier"),
                "roi": row["backtestMetrics"].get("roi"),
                "hitRate": row["backtestMetrics"].get("hitRate"),
                "maxDrawdown": row["backtestMetrics"].get("maxDrawdown"),
                "betCount": row["backtestMetrics"].get("betCount"),
            }
            for row in report["modelLines"]
        ],
    }


if __name__ == "__main__":
    main()
