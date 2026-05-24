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
    args = parser.parse_args()

    result = train_baseline_models(
        args.db,
        artifact_dir=args.artifact_dir,
        limit=args.limit,
        odds_mode=args.odds_mode,
        odds_db_path=args.odds_db,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
