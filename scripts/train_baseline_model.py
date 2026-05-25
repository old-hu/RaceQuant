import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.quant.models.baseline import train_baseline_models


def main() -> None:
    parser = argparse.ArgumentParser(description="训练第一版胜率/位置概率 baseline 模型。")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("models/baseline"))
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--odds-mode", choices=["none", "pre_start_latest", "result_final"], default="none")
    parser.add_argument("--odds-db", type=Path, default=Path("data/processed/legacy_horse_odds.sqlite"))
    parser.add_argument("--allow-result-final", action="store_true", help="Allow result_final odds mode for leakage/control experiments.")
    parser.add_argument("--training-dataset-version", default="baseline_training_v1")
    parser.add_argument("--feature-version", default="runner_features_v1")
    parser.add_argument("--data-build-id")
    args = parser.parse_args()
    if args.odds_mode == "result_final" and not args.allow_result_final:
        parser.error("--odds-mode result_final uses post-race odds and requires --allow-result-final.")

    result = train_baseline_models(
        args.db,
        artifact_dir=args.artifact_dir,
        limit=args.limit,
        odds_mode=args.odds_mode,
        odds_db_path=args.odds_db,
        training_dataset_version=args.training_dataset_version,
        feature_version=args.feature_version,
        data_build_id=args.data_build_id,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
