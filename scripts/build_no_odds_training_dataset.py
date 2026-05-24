from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.quant.features.engine import FeatureEngine
from app.quant.models.baseline import build_training_frame, feature_columns_for_odds_mode


def main() -> None:
    parser = argparse.ArgumentParser(description="生成不含赔率的模型训练宽表。")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--output", type=Path, default=Path("data/features/no_odds_training_dataset.csv"))
    parser.add_argument("--metadata-output", type=Path, default=Path("data/features/no_odds_training_dataset.json"))
    args = parser.parse_args()

    rows = FeatureEngine(args.db, odds_mode="none").build_runner_features(limit=args.limit)
    frame = build_training_frame(args.db, rows)
    feature_columns = feature_columns_for_odds_mode("none")
    ordered_columns = [
        "race_date",
        "racecourse",
        "race_no",
        "horse_code",
        "horse_no",
        "horse_name",
        *feature_columns,
        "win_label",
        "place_label",
    ]
    frame = frame[[column for column in ordered_columns if column in frame.columns]]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False, encoding="utf-8")

    metadata = {
        "dataset": "no_odds_training_dataset",
        "row_count": int(len(frame)),
        "feature_columns": feature_columns,
        "label_columns": ["win_label", "place_label"],
        "source_db": str(args.db),
        "output": str(args.output),
        "coverage": dataset_coverage(frame),
        "sample_rows": [asdict(row) for row in rows[:3]],
    }
    args.metadata_output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: metadata[key] for key in ["row_count", "feature_columns", "coverage", "output"]}, ensure_ascii=False, indent=2))


def dataset_coverage(frame) -> dict[str, float | int]:
    if frame.empty:
        return {"rows": 0}
    coverage = {"rows": int(len(frame))}
    for column in frame.columns:
        if column.endswith("_label"):
            continue
        coverage[f"{column}_not_null"] = round(float(frame[column].notna().mean()), 6)
    return coverage


if __name__ == "__main__":
    main()
