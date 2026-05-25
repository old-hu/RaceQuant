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
    parser.add_argument("--transaction-cost-rate", type=float, default=0.0)
    parser.add_argument("--slippage-rate", type=float, default=0.0)
    parser.add_argument("--min-probability", type=float, default=0.0)
    parser.add_argument("--min-edge", type=float, default=0.03)
    parser.add_argument("--no-min-edge", action="store_true")
    parser.add_argument("--min-pool-size", type=float, default=0.0)
    parser.add_argument("--rules-json", help="JSON object with per-bet-type rule overrides.")
    parser.add_argument("--top-n-per-race", type=int, default=1)
    parser.add_argument("--model-name")
    parser.add_argument("--model-version")
    parser.add_argument("--training-dataset-version")
    parser.add_argument("--feature-version")
    parser.add_argument("--odds-mode")
    parser.add_argument("--allow-result-final", action="store_true", help="Allow result_final odds mode for leakage/control experiments.")
    parser.add_argument("--data-build-id")
    parser.add_argument("--backtest-version", default="backtest_engine_v1")
    parser.add_argument("--race-date-from")
    parser.add_argument("--race-date-to")
    parser.add_argument("--racecourse")
    parser.add_argument("--output", type=Path, default=Path("data/reports/backtest_latest.json"))
    args = parser.parse_args()
    if args.odds_mode == "result_final" and not args.allow_result_final:
        parser.error("--odds-mode result_final uses post-race odds and requires --allow-result-final.")

    rules = json.loads(args.rules_json) if args.rules_json else {}
    config = BacktestConfig(
        bet_type=args.bet_type,
        stake_strategy=args.stake_strategy,
        initial_bankroll=args.initial_bankroll,
        flat_stake=args.flat_stake,
        kelly_fraction=args.kelly_fraction,
        max_stake_fraction=args.max_stake_fraction,
        transaction_cost_rate=args.transaction_cost_rate,
        slippage_rate=args.slippage_rate,
        min_probability=args.min_probability,
        min_edge=None if args.no_min_edge else args.min_edge,
        safety_margin_by_bet_type=rules.get("safety_margin_by_bet_type", {}),
        min_probability_by_bet_type=rules.get("min_probability_by_bet_type", {}),
        min_pool_size=args.min_pool_size,
        min_pool_size_by_bet_type=rules.get("min_pool_size_by_bet_type", {}),
        min_odds_by_bet_type=rules.get("min_odds_by_bet_type", {}),
        max_odds_by_bet_type=rules.get("max_odds_by_bet_type", {}),
        top_n_per_race=args.top_n_per_race,
        model_name=args.model_name,
        model_version=args.model_version,
        training_dataset_version=args.training_dataset_version,
        feature_version=args.feature_version,
        odds_mode=args.odds_mode,
        data_build_id=args.data_build_id,
        backtest_version=args.backtest_version,
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

