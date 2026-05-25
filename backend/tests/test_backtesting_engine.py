import json
import sqlite3
from pathlib import Path

from app.quant.backtesting.engine import BacktestConfig, BacktestEngine, Prediction, result_to_dict, run_backtest_from_db


def test_flat_win_backtest_metrics(tmp_path: Path) -> None:
    db_path = tmp_path / "backtest.sqlite"
    build_backtest_db(db_path)

    result = run_backtest_from_db(
        db_path,
        BacktestConfig(
            bet_type="win",
            stake_strategy="flat",
            flat_stake=10,
            initial_bankroll=100,
            max_stake_fraction=1.0,
            min_edge=0.01,
            top_n_per_race=1,
        ),
    )

    assert result.metrics["betCount"] == 2
    assert result.metrics["turnover"] == 20
    assert result.metrics["profitLoss"] == 6
    assert result.metrics["roi"] == 0.3
    assert result.metrics["hitRate"] == 0.5
    assert result.metrics["maxDrawdown"] > 0
    assert result.metrics["averageOdds"] == 2.76515
    assert [bet.is_hit for bet in result.bets] == [True, False]
    assert result.equity_curve[-1].bankroll == 106


def test_place_and_fractional_kelly_backtest(tmp_path: Path) -> None:
    db_path = tmp_path / "backtest.sqlite"
    build_backtest_db(db_path)

    result = run_backtest_from_db(
        db_path,
        BacktestConfig(
            bet_type="place",
            stake_strategy="fractional_kelly",
            initial_bankroll=1000,
            kelly_fraction=0.5,
            max_stake_fraction=0.05,
            min_edge=None,
            min_probability=0.5,
            top_n_per_race=1,
        ),
    )

    assert result.metrics["betCount"] == 2
    assert all(bet.bet_type == "place" for bet in result.bets)
    assert all(bet.stake <= 55 for bet in result.bets)
    assert result.metrics["hitRate"] == 1.0
    assert result.metrics["profitLoss"] > 0


def test_win_value_betting_requires_edge_above_margin() -> None:
    engine = BacktestEngine(BacktestConfig(bet_type="win", min_edge=0.03, top_n_per_race=10))

    selected = engine.select_bets(
        [
            prediction_object("A001", "1", 0.25, edge=None),
            prediction_object("A002", "2", 0.24, edge=0.029),
            prediction_object("A003", "3", 0.23, edge=0.03),
            prediction_object("A004", "4", 0.22, edge=0.05),
        ]
    )

    assert [item.horse_code for item in selected] == ["A004", "A003"]


def test_fractional_kelly_respects_positive_edge_and_stake_cap() -> None:
    engine = BacktestEngine(
        BacktestConfig(
            bet_type="win",
            stake_strategy="fractional_kelly",
            initial_bankroll=1000,
            kelly_fraction=1.0,
            max_stake_fraction=0.02,
        )
    )

    capped = engine.calculate_stake(prediction_object("A001", "1", 0.6, edge=0.1), decimal_odds=3.0, bankroll=1000)
    no_edge = engine.calculate_stake(prediction_object("A002", "2", 0.2, edge=-0.1), decimal_odds=3.0, bankroll=1000)
    invalid_odds = engine.calculate_stake(prediction_object("A003", "3", 0.9, edge=0.1), decimal_odds=1.0, bankroll=1000)

    assert capped == 20
    assert no_edge == 0
    assert invalid_odds == 0


def test_backtest_applies_transaction_cost_slippage_and_flat_stake_cap(tmp_path: Path) -> None:
    db_path = tmp_path / "backtest.sqlite"
    build_backtest_db(db_path)

    result = run_backtest_from_db(
        db_path,
        BacktestConfig(
            bet_type="win",
            stake_strategy="flat",
            flat_stake=100,
            initial_bankroll=1000,
            max_stake_fraction=0.01,
            transaction_cost_rate=0.05,
            slippage_rate=0.1,
            min_edge=0.01,
            top_n_per_race=1,
        ),
    )

    assert result.metrics["betCount"] == 2
    assert [bet.stake for bet in result.bets] == [10, 10.129]
    assert result.bets[0].decimal_odds == 2.25
    assert result.bets[0].profit_loss == 12.9
    assert result.bets[1].profit_loss == -10.6354
    assert result.metrics["profitLoss"] == 2.2646
    assert any("5.00%" in assumption for assumption in result.assumptions)
    assert any("10.00%" in assumption for assumption in result.assumptions)


def test_bet_type_rules_filter_probability_edge_odds_and_liquidity() -> None:
    engine = BacktestEngine(
        BacktestConfig(
            bet_type="win",
            min_edge=0.0,
            min_probability=0.0,
            safety_margin_by_bet_type={"win": 0.04},
            min_probability_by_bet_type={"win": 0.2},
            min_pool_size_by_bet_type={"win": 100_000},
            min_odds_by_bet_type={"win": 2.0},
            max_odds_by_bet_type={"win": 8.0},
            top_n_per_race=10,
        )
    )

    selected = engine.select_bets(
        [
            prediction_object("A001", "1", 0.3, edge=0.05, pool_size=150_000),
            prediction_object("A002", "2", 0.19, edge=0.2, pool_size=150_000),
            prediction_object("A003", "3", 0.3, edge=0.03, pool_size=150_000),
            prediction_object("A004", "4", 0.3, edge=0.05, pool_size=50_000),
            prediction_object("A005", "5", 0.8, edge=0.05, pool_size=150_000),
            prediction_object("A006", "6", 0.15, edge=0.13, pool_size=150_000),
        ]
    )

    assert [item.horse_code for item in selected] == ["A001"]


def test_candidate_explanations_include_selected_and_filter_reasons() -> None:
    engine = BacktestEngine(
        BacktestConfig(
            bet_type="win",
            safety_margin_by_bet_type={"win": 0.04},
            min_probability_by_bet_type={"win": 0.2},
            min_pool_size_by_bet_type={"win": 100_000},
            top_n_per_race=1,
        )
    )

    selected, explanations = engine.evaluate_predictions(
        [
            prediction_object("A001", "1", 0.3, edge=0.05, pool_size=150_000, feature_contributions={"draw": 0.12, "jockey": -0.05}),
            prediction_object("A002", "2", 0.19, edge=0.2, pool_size=150_000),
            prediction_object("A003", "3", 0.3, edge=0.03, pool_size=150_000),
            prediction_object("A004", "4", 0.3, edge=0.05, pool_size=50_000),
            prediction_object("A005", "5", 0.31, edge=0.06, pool_size=150_000),
        ]
    )
    by_horse = {item.horse_code: item for item in explanations}

    assert [item.horse_code for item in selected] == ["A005"]
    assert by_horse["A005"].status == "selected"
    assert by_horse["A001"].status == "not_selected"
    assert by_horse["A001"].filter_reason == "outside_top_n_per_race"
    assert by_horse["A001"].feature_contributions == {"draw": 0.12, "jockey": -0.05}
    assert by_horse["A002"].filter_reason == "below_min_probability"
    assert by_horse["A003"].filter_reason == "below_safety_margin"
    assert by_horse["A004"].filter_reason == "below_min_pool_size"


def test_backtest_result_serializes_candidate_explanations(tmp_path: Path) -> None:
    db_path = tmp_path / "backtest.sqlite"
    build_backtest_db(db_path)

    result = run_backtest_from_db(
        db_path,
        BacktestConfig(
            bet_type="win",
            stake_strategy="flat",
            flat_stake=10,
            initial_bankroll=100,
            max_stake_fraction=1.0,
            min_edge=0.01,
            top_n_per_race=1,
        ),
    )
    payload = result_to_dict(result)

    assert payload["candidateExplanations"]
    assert {"model_probability", "market_probability", "fair_odds", "edge", "filter_reason"} <= set(payload["candidateExplanations"][0])


def test_backtest_config_records_version_bindings(tmp_path: Path) -> None:
    db_path = tmp_path / "backtest.sqlite"
    build_backtest_db(db_path)

    result = run_backtest_from_db(
        db_path,
        BacktestConfig(
            bet_type="win",
            min_edge=0.01,
            training_dataset_version="dataset-v1",
            feature_version="features-v1",
            odds_mode="pre_start_latest",
            data_build_id="build-v1",
            backtest_version="backtest-v1",
        ),
    )
    payload = result_to_dict(result)

    assert payload["config"]["training_dataset_version"] == "dataset-v1"
    assert payload["config"]["feature_version"] == "features-v1"
    assert payload["config"]["odds_mode"] == "pre_start_latest"
    assert payload["config"]["data_build_id"] == "build-v1"
    assert payload["config"]["backtest_version"] == "backtest-v1"
    assert any("backtest-v1" in assumption for assumption in payload["assumptions"])


def test_place_rules_use_place_market_probability_for_edge() -> None:
    engine = BacktestEngine(
        BacktestConfig(
            bet_type="place",
            min_edge=None,
            safety_margin_by_bet_type={"place": 0.08},
            min_probability_by_bet_type={"place": 0.55},
            min_pool_size_by_bet_type={"place": 20_000},
            top_n_per_race=10,
        )
    )

    selected = engine.select_bets(
        [
            prediction_object("P001", "1", 0.25, edge=None, place_probability=0.7, market_place_probability=0.55, place_pool_size=30_000),
            prediction_object("P002", "2", 0.25, edge=None, place_probability=0.7, market_place_probability=0.65, place_pool_size=30_000),
            prediction_object("P003", "3", 0.25, edge=None, place_probability=0.52, market_place_probability=0.4, place_pool_size=30_000),
            prediction_object("P004", "4", 0.25, edge=None, place_probability=0.7, market_place_probability=0.55, place_pool_size=10_000),
        ]
    )

    assert [item.horse_code for item in selected] == ["P001"]


def build_backtest_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE model_predictions (
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            horse_code TEXT NOT NULL,
            model_name TEXT NOT NULL,
            model_version TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (race_date, racecourse, race_no, horse_code, model_name, model_version)
        );

        CREATE TABLE race_results (
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            place TEXT NOT NULL,
            horse_no TEXT,
            horse_name TEXT,
            horse_code TEXT,
            win_odds TEXT,
            PRIMARY KEY (race_date, racecourse, race_no, place, horse_no)
        );

        CREATE TABLE dividends (
            race_date TEXT NOT NULL,
            racecourse TEXT,
            race_no INTEGER NOT NULL,
            pool TEXT NOT NULL,
            winning_combination TEXT NOT NULL,
            dividend TEXT NOT NULL,
            PRIMARY KEY (race_date, race_no, pool, winning_combination, dividend)
        );
        """
    )
    predictions = [
        prediction("2026-05-20", 1, "A001", "1", "Winner", 0.55, 0.8, 0.15),
        prediction("2026-05-20", 1, "A002", "2", "Runner", 0.2, 0.55, -0.05),
        prediction("2026-05-20", 2, "B001", "3", "Beaten", 0.45, 0.7, 0.12),
        prediction("2026-05-20", 2, "B002", "4", "Actual", 0.22, 0.6, 0.02),
    ]
    con.executemany(
        """
        INSERT INTO model_predictions (
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
                json.dumps(item),
            )
            for item in predictions
        ],
    )
    con.executemany(
        """
        INSERT INTO race_results (
            race_date, racecourse, race_no, place, horse_no, horse_name, horse_code, win_odds
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-05-20", "HV", 1, "1", "1", "Winner", "A001", "2.6"),
            ("2026-05-20", "HV", 1, "2", "2", "Runner", "A002", "6.0"),
            ("2026-05-20", "HV", 2, "1", "4", "Actual", "B002", "4.0"),
            ("2026-05-20", "HV", 2, "2", "3", "Beaten", "B001", "3.0"),
        ],
    )
    con.executemany(
        """
        INSERT INTO dividends (race_date, racecourse, race_no, pool, winning_combination, dividend)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-05-20", "HV", 1, "WIN", "1", "26.00"),
            ("2026-05-20", "HV", 1, "PLACE", "1", "13.00"),
            ("2026-05-20", "HV", 1, "PLACE", "2", "18.00"),
            ("2026-05-20", "HV", 2, "WIN", "4", "40.00"),
            ("2026-05-20", "HV", 2, "PLACE", "3", "18.00"),
            ("2026-05-20", "HV", 2, "PLACE", "4", "16.00"),
        ],
    )
    con.commit()
    con.close()


def prediction(
    race_date: str,
    race_no: int,
    horse_code: str,
    horse_no: str,
    horse_name: str,
    win_probability: float,
    place_probability: float,
    edge: float,
) -> dict:
    return {
        "raceDate": race_date,
        "racecourse": "HV",
        "raceNo": race_no,
        "horseCode": horse_code,
        "horseNo": horse_no,
        "horseName": horse_name,
        "modelName": "baseline-logistic",
        "modelVersion": "test",
        "winProbability": win_probability,
        "placeProbability": place_probability,
        "fairWinOdds": 1 / win_probability,
        "fairPlaceOdds": 1 / place_probability,
        "marketWinProbability": max(0.01, win_probability - edge),
        "edge": edge,
        "isValueBet": edge >= 0.03,
    }


def prediction_object(
    horse_code: str,
    horse_no: str,
    win_probability: float,
    edge: float | None,
    pool_size: float | None = None,
    place_probability: float = 0.5,
    market_place_probability: float | None = None,
    place_pool_size: float | None = None,
    feature_contributions: dict[str, float] | None = None,
) -> Prediction:
    market_probability = None if edge is None else max(0.01, win_probability - edge)
    payload = {}
    if pool_size is not None:
        payload["winPoolSize"] = pool_size
    if place_pool_size is not None:
        payload["placePoolSize"] = place_pool_size
    if feature_contributions is not None:
        payload["featureContributions"] = feature_contributions
    return Prediction(
        race_date="2026-05-20",
        racecourse="HV",
        race_no=1,
        horse_code=horse_code,
        horse_no=horse_no,
        horse_name=f"Horse {horse_no}",
        model_name="baseline-logistic",
        model_version="test",
        win_probability=win_probability,
        place_probability=place_probability,
        fair_win_odds=1 / win_probability,
        fair_place_odds=1 / place_probability,
        market_win_probability=market_probability,
        market_place_probability=market_place_probability,
        edge=edge,
        payload=payload,
    )
