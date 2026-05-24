from __future__ import annotations

import json
import pickle
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.quant.features.engine import FeatureEngine, RunnerFeatureRow


FEATURE_COLUMNS = [
    "recent_3_starts",
    "recent_3_win_rate",
    "recent_3_place_rate",
    "recent_3_avg_finish",
    "recent_5_starts",
    "recent_5_win_rate",
    "recent_5_place_rate",
    "recent_5_avg_finish",
    "days_since_last_run",
    "draw",
    "actual_weight_lbs",
    "declared_horse_weight_lbs",
    "jockey_win_rate",
    "trainer_win_rate",
    "implied_win_probability",
    "distance_m",
    "distance_starts",
    "distance_win_rate",
    "surface_starts",
    "surface_win_rate",
]

NO_ODDS_FEATURE_COLUMNS = [column for column in FEATURE_COLUMNS if column != "implied_win_probability"]
ODDS_FEATURE_COLUMNS = FEATURE_COLUMNS


@dataclass(frozen=True)
class TrainingResult:
    model_name: str
    model_version: str
    row_count: int
    metrics: dict[str, float | None]
    artifact_path: str
    metadata_path: str


def train_baseline_models(
    db_path: Path,
    artifact_dir: Path = Path("models/baseline"),
    limit: int = 10000,
    odds_mode: str = "none",
    odds_db_path: Path | None = None,
) -> TrainingResult:
    rows = FeatureEngine(db_path, odds_mode=odds_mode, odds_db_path=odds_db_path).build_runner_features(limit=limit)
    frame = build_training_frame(db_path, rows)
    if frame.empty:
        raise ValueError("No training rows available.")

    feature_columns = feature_columns_for_odds_mode(odds_mode)
    x = frame[feature_columns].fillna(0.0)
    win_y = frame["win_label"]
    place_y = frame["place_label"]

    win_model = fit_model(x, win_y)
    place_model = fit_model(x, place_y)

    win_prob = probability(win_model, x)
    place_prob = probability(place_model, x)
    metrics = {
        "win_log_loss": safe_log_loss(win_y, win_prob),
        "win_brier": brier_score_loss(win_y, win_prob),
        "win_auc": safe_auc(win_y, win_prob),
        "place_log_loss": safe_log_loss(place_y, place_prob),
        "place_brier": brier_score_loss(place_y, place_prob),
        "place_auc": safe_auc(place_y, place_prob),
    }

    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_suffix = "no_odds" if odds_mode == "none" else "pre_start_odds" if odds_mode == "pre_start_latest" else "result_final_odds"
    model_name = f"baseline-logistic-{model_suffix}"
    artifact_path = artifact_dir / f"{model_suffix}_{model_version}.pkl"
    metadata_path = artifact_dir / f"{model_suffix}_{model_version}.json"
    artifact = {
        "model_name": model_name,
        "model_version": model_version,
        "odds_mode": odds_mode,
        "feature_columns": feature_columns,
        "win_model": win_model,
        "place_model": place_model,
    }
    artifact_path.write_bytes(pickle.dumps(artifact))
    metadata = {
        "model_name": model_name,
        "model_version": model_version,
        "odds_mode": odds_mode,
        "row_count": len(frame),
        "metrics": metrics,
        "feature_columns": feature_columns,
        "artifact_path": str(artifact_path),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return TrainingResult(
        model_name=model_name,
        model_version=model_version,
        row_count=len(frame),
        metrics=metrics,
        artifact_path=str(artifact_path),
        metadata_path=str(metadata_path),
    )


def fit_model(x: pd.DataFrame, y: pd.Series) -> CalibratedClassifierCV | Pipeline:
    base = Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    if y.nunique() < 2 or len(y) < 20:
        base.fit(x, y)
        return base
    calibrated = CalibratedClassifierCV(base, method="sigmoid", cv=min(3, int(y.value_counts().min())))
    calibrated.fit(x, y)
    return calibrated


def feature_columns_for_odds_mode(odds_mode: str) -> list[str]:
    if odds_mode == "none":
        return NO_ODDS_FEATURE_COLUMNS
    return ODDS_FEATURE_COLUMNS


def build_training_frame(db_path: Path, rows: list[RunnerFeatureRow]) -> pd.DataFrame:
    labels = labels_by_runner(db_path)
    records = []
    for row in rows:
        key = (row.race_date, row.racecourse, row.race_no, row.horse_code)
        label = labels.get(key)
        if label is None:
            continue
        record = asdict(row)
        record.update(label)
        records.append(record)
    return pd.DataFrame.from_records(records)


def labels_by_runner(db_path: Path) -> dict[tuple[str, str, int, str], dict[str, int]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT race_date, racecourse, race_no, horse_code, place
        FROM race_results
        WHERE horse_code IS NOT NULL
        """
    ).fetchall()
    con.close()
    labels = {}
    for row in rows:
        place = int(row["place"]) if str(row["place"]).isdigit() else 999
        labels[(row["race_date"], row["racecourse"], row["race_no"], row["horse_code"])] = {
            "win_label": 1 if place == 1 else 0,
            "place_label": 1 if place <= 3 else 0,
        }
    return labels


def load_artifact(path: Path) -> dict[str, Any]:
    return pickle.loads(path.read_bytes())


def predict_with_artifact(artifact: dict[str, Any], rows: list[RunnerFeatureRow]) -> list[dict[str, Any]]:
    frame = pd.DataFrame.from_records([asdict(row) for row in rows])
    if frame.empty:
        return []
    x = frame[artifact["feature_columns"]].fillna(0.0)
    win_probs = probability(artifact["win_model"], x)
    place_probs = probability(artifact["place_model"], x)
    predictions = []
    for index, row in frame.iterrows():
        win_probability = float(win_probs[index])
        place_probability = float(place_probs[index])
        market_probability = row.get("implied_win_probability") or None
        fair_win_odds = (1 / win_probability) if win_probability > 0 else None
        edge = (win_probability - market_probability) if market_probability is not None else None
        predictions.append(
            {
                "raceDate": row["race_date"],
                "racecourse": row["racecourse"],
                "raceNo": int(row["race_no"]),
                "horseCode": row["horse_code"],
                "horseNo": row["horse_no"],
                "horseName": row["horse_name"],
                "modelName": artifact["model_name"],
                "modelVersion": artifact["model_version"],
                "winProbability": win_probability,
                "placeProbability": place_probability,
                "fairWinOdds": fair_win_odds,
                "fairPlaceOdds": (1 / place_probability) if place_probability > 0 else None,
                "marketWinProbability": market_probability,
                "edge": edge,
                "isValueBet": bool(edge is not None and edge >= 0.03),
            }
        )
    return predictions


def probability(model: Any, x: pd.DataFrame) -> pd.Series:
    probabilities = model.predict_proba(x)
    if probabilities.shape[1] == 1:
        return pd.Series([float(model.classes_[0])] * len(x))
    class_index = list(model.classes_).index(1)
    return pd.Series(probabilities[:, class_index])


def safe_log_loss(y_true: pd.Series, y_prob: pd.Series) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(log_loss(y_true, y_prob))


def safe_auc(y_true: pd.Series, y_prob: pd.Series) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(roc_auc_score(y_true, y_prob))
