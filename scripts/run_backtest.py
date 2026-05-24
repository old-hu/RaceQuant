import argparse
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.quant.backtesting.engine import BacktestConfig, result_to_dict, run_backtest_from_db


def main() -> None:
    parser = argparse.ArgumentParser(description="运行赛马量化回测。")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--bet-type", choices=["win", "place"], default="win")
    parser.add_argument("--stake-strategy", choices=["flat", "fractional_kelly"], default="flat")
    parser.add_argument("--initial-bankroll", type=float, default=10_000)
    parser.add_argument("--flat-stake", type=float, default=10)
    parser.add_argument("--kelly-fraction", type=float, default=0.25)
    parser.add_argument("--max-stake-fraction", type=float, default=0.02)
    parser.add_argument("--min-probability", type=float, default=0.0)
    parser.add_argument("--min-edge", type=float, default=0.03)
    parser.add_argument("--no-min-edge", action="store_true")
    parser.add_argument("--top-n-per-race", type=int, default=1)
    parser.add_argument("--model-name")
    parser.add_argument("--model-version")
    parser.add_argument("--race-date-from")
    parser.add_argument("--race-date-to")
    parser.add_argument("--racecourse")
    parser.add_argument("--output", type=Path, default=Path("data/reports/backtest_latest.json"))
    args = parser.parse_args()

    config = BacktestConfig(
        bet_type=args.bet_type,
        stake_strategy=args.stake_strategy,
        initial_bankroll=args.initial_bankroll,
        flat_stake=args.flat_stake,
        kelly_fraction=args.kelly_fraction,
        max_stake_fraction=args.max_stake_fraction,
        min_probability=args.min_probability,
        min_edge=None if args.no_min_edge else args.min_edge,
        top_n_per_race=args.top_n_per_race,
        model_name=args.model_name,
        model_version=args.model_version,
        race_date_from=args.race_date_from,
        race_date_to=args.race_date_to,
        racecourse=args.racecourse,
    )
    result = result_to_dict(run_backtest_from_db(args.db, config))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    print(f"Wrote backtest report to {args.output}")


if __name__ == "__main__":
    main()

