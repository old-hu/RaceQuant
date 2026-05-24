import json
import sqlite3
from pathlib import Path

from app.quant.backtesting.engine import BacktestConfig, run_backtest_from_db


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
