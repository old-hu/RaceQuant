from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.quant.backtesting.engine import BacktestConfig, result_to_dict, run_backtest_from_db


def get_connection() -> sqlite3.Connection:
    db_path = Path(settings.hkjc_structured_db_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[3] / db_path
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    init_schema(con)
    return con


def init_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS api_backtest_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            parameters_json TEXT NOT NULL,
            roi REAL,
            hit_rate REAL,
            max_drawdown REAL,
            bet_count INTEGER,
            turnover REAL,
            profit_loss REAL,
            profit_factor REAL,
            average_odds REAL,
            final_bankroll REAL,
            assumptions_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS api_backtest_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            horse_code TEXT NOT NULL,
            horse_no TEXT NOT NULL,
            horse_name TEXT NOT NULL,
            bet_type TEXT NOT NULL,
            model_probability REAL NOT NULL,
            market_probability REAL,
            edge REAL,
            stake REAL NOT NULL,
            decimal_odds REAL,
            payout REAL NOT NULL,
            profit_loss REAL NOT NULL,
            bankroll_after REAL NOT NULL,
            is_hit INTEGER NOT NULL,
            FOREIGN KEY (run_id) REFERENCES api_backtest_runs(id)
        );

        CREATE TABLE IF NOT EXISTS api_backtest_equity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            race_no INTEGER NOT NULL,
            bankroll REAL NOT NULL,
            drawdown REAL NOT NULL,
            FOREIGN KEY (run_id) REFERENCES api_backtest_runs(id)
        );
        """
    )
    ensure_columns(
        con,
        "api_backtest_runs",
        {
            "turnover": "REAL",
            "profit_loss": "REAL",
            "profit_factor": "REAL",
            "average_odds": "REAL",
            "final_bankroll": "REAL",
            "assumptions_json": "TEXT",
        },
    )
    con.commit()


def ensure_columns(con: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def create_run(name: str, strategy_name: str, parameters: dict[str, Any], execute: bool = True) -> dict[str, Any]:
    with get_connection() as con:
        cur = con.execute(
            """
            INSERT INTO api_backtest_runs (name, strategy_name, parameters_json)
            VALUES (?, ?, ?)
            """,
            (name, strategy_name, json.dumps(parameters, ensure_ascii=False, sort_keys=True)),
        )
        con.commit()
        run_id = int(cur.lastrowid)
        if execute:
            try:
                run_backtest(run_id, con=con)
            except Exception as exc:  # noqa: BLE001 - persist failures for API consumers.
                con.execute(
                    """
                    UPDATE api_backtest_runs
                    SET status = 'failed', assumptions_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (json.dumps([str(exc)], ensure_ascii=False), run_id),
                )
                con.commit()
        return get_run(run_id, con=con)


def run_backtest(run_id: int, con: sqlite3.Connection | None = None) -> dict[str, Any]:
    should_close = con is None
    con = con or get_connection()
    try:
        run = get_run(run_id, con=con)
        if run is None:
            raise ValueError(f"Backtest run {run_id} does not exist.")
        config = config_from_parameters(run["strategyName"], run["parameters"])
        db_path = structured_db_path()
        result = run_backtest_from_db(db_path, config)
        payload = result_to_dict(result)
        metrics = payload["metrics"]
        con.execute("DELETE FROM api_backtest_bets WHERE run_id = ?", (run_id,))
        con.execute("DELETE FROM api_backtest_equity WHERE run_id = ?", (run_id,))
        con.executemany(
            """
            INSERT INTO api_backtest_bets (
                run_id, sequence, race_date, racecourse, race_no, horse_code, horse_no, horse_name,
                bet_type, model_probability, market_probability, edge, stake, decimal_odds,
                payout, profit_loss, bankroll_after, is_hit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    bet["sequence"],
                    bet["race_date"],
                    bet["racecourse"],
                    bet["race_no"],
                    bet["horse_code"],
                    bet["horse_no"],
                    bet["horse_name"],
                    bet["bet_type"],
                    bet["model_probability"],
                    bet["market_probability"],
                    bet["edge"],
                    bet["stake"],
                    bet["decimal_odds"],
                    bet["payout"],
                    bet["profit_loss"],
                    bet["bankroll_after"],
                    1 if bet["is_hit"] else 0,
                )
                for bet in payload["bets"]
            ],
        )
        con.executemany(
            """
            INSERT INTO api_backtest_equity (
                run_id, sequence, race_date, racecourse, race_no, bankroll, drawdown
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    point["sequence"],
                    point["race_date"],
                    point["racecourse"],
                    point["race_no"],
                    point["bankroll"],
                    point["drawdown"],
                )
                for point in payload["equityCurve"]
            ],
        )
        con.execute(
            """
            UPDATE api_backtest_runs
            SET status = 'completed',
                roi = ?,
                hit_rate = ?,
                max_drawdown = ?,
                bet_count = ?,
                turnover = ?,
                profit_loss = ?,
                profit_factor = ?,
                average_odds = ?,
                final_bankroll = ?,
                assumptions_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                metrics["roi"],
                metrics["hitRate"],
                metrics["maxDrawdown"],
                metrics["betCount"],
                metrics["turnover"],
                metrics["profitLoss"],
                metrics["profitFactor"],
                metrics["averageOdds"],
                metrics["finalBankroll"],
                json.dumps(payload["assumptions"], ensure_ascii=False),
                run_id,
            ),
        )
        con.commit()
        return get_run(run_id, con=con) or {}
    finally:
        if should_close:
            con.close()


def list_runs(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    with get_connection() as con:
        rows = con.execute(
            """
            SELECT * FROM api_backtest_runs
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [normalize_run(row) for row in rows]


def get_run(run_id: int, con: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    should_close = con is None
    con = con or get_connection()
    try:
        row = con.execute("SELECT * FROM api_backtest_runs WHERE id = ?", (run_id,)).fetchone()
        return normalize_run(row) if row else None
    finally:
        if should_close:
            con.close()


def normalize_run(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["parameters"] = json.loads(payload.pop("parameters_json"))
    payload["assumptions"] = json.loads(payload.pop("assumptions_json") or "[]")
    payload["strategyName"] = payload.pop("strategy_name")
    payload["hitRate"] = payload.pop("hit_rate")
    payload["maxDrawdown"] = payload.pop("max_drawdown")
    payload["betCount"] = payload.pop("bet_count")
    payload["profitLoss"] = payload.pop("profit_loss")
    payload["profitFactor"] = payload.pop("profit_factor")
    payload["averageOdds"] = payload.pop("average_odds")
    payload["finalBankroll"] = payload.pop("final_bankroll")
    return payload


def get_results(run_id: int) -> dict[str, Any] | None:
    with get_connection() as con:
        run = get_run(run_id, con=con)
        if run is None:
            return None
        bets = [normalize_bet(row) for row in con.execute("SELECT * FROM api_backtest_bets WHERE run_id = ? ORDER BY sequence", (run_id,)).fetchall()]
        equity = [
            normalize_equity(row)
            for row in con.execute("SELECT * FROM api_backtest_equity WHERE run_id = ? ORDER BY sequence", (run_id,)).fetchall()
        ]
        return {"run": run, "bets": bets, "equityCurve": equity, "assumptions": run["assumptions"]}


def normalize_bet(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload.pop("id", None)
    payload.pop("run_id", None)
    payload["raceNo"] = payload.pop("race_no")
    payload["horseCode"] = payload.pop("horse_code")
    payload["horseNo"] = payload.pop("horse_no")
    payload["horseName"] = payload.pop("horse_name")
    payload["betType"] = payload.pop("bet_type")
    payload["modelProbability"] = payload.pop("model_probability")
    payload["marketProbability"] = payload.pop("market_probability")
    payload["decimalOdds"] = payload.pop("decimal_odds")
    payload["profitLoss"] = payload.pop("profit_loss")
    payload["bankrollAfter"] = payload.pop("bankroll_after")
    payload["isHit"] = bool(payload.pop("is_hit"))
    return payload


def normalize_equity(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload.pop("id", None)
    payload.pop("run_id", None)
    payload["raceNo"] = payload.pop("race_no")
    return payload


def config_from_parameters(strategy_name: str, parameters: dict[str, Any]) -> BacktestConfig:
    merged = dict(parameters)
    normalized = strategy_name.lower().replace("_", "-")
    if "place" in normalized:
        merged.setdefault("bet_type", "place")
    else:
        merged.setdefault("bet_type", "win")
    if "kelly" in normalized:
        merged.setdefault("stake_strategy", "fractional_kelly")
    else:
        merged.setdefault("stake_strategy", "flat")
    aliases = {
        "betType": "bet_type",
        "stakeStrategy": "stake_strategy",
        "initialBankroll": "initial_bankroll",
        "flatStake": "flat_stake",
        "stake": "flat_stake",
        "kellyFraction": "kelly_fraction",
        "maxStakeFraction": "max_stake_fraction",
        "minProbability": "min_probability",
        "minEdge": "min_edge",
        "topNPerRace": "top_n_per_race",
        "modelName": "model_name",
        "modelVersion": "model_version",
        "raceDateFrom": "race_date_from",
        "raceDateTo": "race_date_to",
    }
    for old, new in aliases.items():
        if old in merged and new not in merged:
            merged[new] = merged.pop(old)
    allowed = BacktestConfig.__dataclass_fields__.keys()
    return BacktestConfig(**{key: value for key, value in merged.items() if key in allowed})


def structured_db_path() -> Path:
    db_path = Path(settings.hkjc_structured_db_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[3] / db_path
    return db_path
