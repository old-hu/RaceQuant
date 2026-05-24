from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


BetType = Literal["win", "place"]
StakeStrategy = Literal["flat", "fractional_kelly"]


@dataclass(frozen=True)
class BacktestConfig:
    bet_type: BetType = "win"
    stake_strategy: StakeStrategy = "flat"
    initial_bankroll: float = 10_000.0
    flat_stake: float = 10.0
    kelly_fraction: float = 0.25
    max_stake_fraction: float = 0.02
    min_probability: float = 0.0
    min_edge: float | None = 0.03
    top_n_per_race: int = 1
    model_name: str | None = None
    model_version: str | None = None
    race_date_from: str | None = None
    race_date_to: str | None = None
    racecourse: str | None = None


@dataclass(frozen=True)
class Prediction:
    race_date: str
    racecourse: str
    race_no: int
    horse_code: str
    horse_no: str
    horse_name: str
    model_name: str
    model_version: str
    win_probability: float
    place_probability: float
    fair_win_odds: float | None
    fair_place_odds: float | None
    market_win_probability: float | None
    edge: float | None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RaceResult:
    race_date: str
    racecourse: str
    race_no: int
    horse_code: str | None
    horse_no: str | None
    place: int | None
    win_odds: float | None


@dataclass(frozen=True)
class Dividend:
    race_date: str
    racecourse: str | None
    race_no: int
    pool: str
    winning_combination: str
    dividend: float


@dataclass(frozen=True)
class BetRecord:
    sequence: int
    race_date: str
    racecourse: str
    race_no: int
    horse_code: str
    horse_no: str
    horse_name: str
    bet_type: BetType
    model_probability: float
    market_probability: float | None
    edge: float | None
    stake: float
    decimal_odds: float | None
    payout: float
    profit_loss: float
    bankroll_after: float
    is_hit: bool


@dataclass(frozen=True)
class EquityPoint:
    sequence: int
    race_date: str
    racecourse: str
    race_no: int
    bankroll: float
    drawdown: float


@dataclass(frozen=True)
class BacktestResult:
    config: BacktestConfig
    metrics: dict[str, float | int | None]
    bets: list[BetRecord]
    equity_curve: list[EquityPoint]
    assumptions: list[str]


def run_backtest_from_db(db_path: Path, config: BacktestConfig) -> BacktestResult:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        predictions = load_predictions(con, config)
        results = load_results(con)
        dividends = load_dividends(con)
    finally:
        con.close()
    return BacktestEngine(config).run(predictions, results, dividends)


class BacktestEngine:
    def __init__(self, config: BacktestConfig) -> None:
        self.config = config

    def run(
        self,
        predictions: list[Prediction],
        results: list[RaceResult],
        dividends: list[Dividend],
    ) -> BacktestResult:
        result_index = index_results(results)
        dividend_index = index_dividends(dividends)
        candidates = self.select_bets(predictions)
        bankroll = self.config.initial_bankroll
        high_watermark = bankroll
        bets: list[BetRecord] = []
        equity_curve: list[EquityPoint] = []

        for candidate in candidates:
            result = find_result(candidate, result_index)
            if result is None:
                continue
            entry_odds = entry_decimal_odds(candidate, self.config.bet_type)
            settlement_decimal_odds = settlement_odds(candidate, self.config.bet_type, result, dividend_index)
            if settlement_decimal_odds is None or settlement_decimal_odds <= 1:
                continue
            stake = self.calculate_stake(candidate, entry_odds or settlement_decimal_odds, bankroll)
            if stake <= 0:
                continue

            is_hit = is_winning_bet(result, self.config.bet_type)
            payout = stake * settlement_decimal_odds if is_hit else 0.0
            profit_loss = payout - stake
            bankroll += profit_loss
            high_watermark = max(high_watermark, bankroll)
            drawdown = (high_watermark - bankroll) / high_watermark if high_watermark > 0 else 0.0
            sequence = len(bets) + 1
            market_probability = (1 / entry_odds) if entry_odds and entry_odds > 0 else None
            probability = probability_for(candidate, self.config.bet_type)
            edge = edge_for(candidate, self.config.bet_type, entry_odds)
            bets.append(
                BetRecord(
                    sequence=sequence,
                    race_date=candidate.race_date,
                    racecourse=candidate.racecourse,
                    race_no=candidate.race_no,
                    horse_code=candidate.horse_code,
                    horse_no=candidate.horse_no,
                    horse_name=candidate.horse_name,
                    bet_type=self.config.bet_type,
                    model_probability=probability,
                    market_probability=market_probability,
                    edge=edge,
                    stake=round(stake, 4),
                    decimal_odds=round(entry_odds or settlement_decimal_odds, 4),
                    payout=round(payout, 4),
                    profit_loss=round(profit_loss, 4),
                    bankroll_after=round(bankroll, 4),
                    is_hit=is_hit,
                )
            )
            equity_curve.append(
                EquityPoint(
                    sequence=sequence,
                    race_date=candidate.race_date,
                    racecourse=candidate.racecourse,
                    race_no=candidate.race_no,
                    bankroll=round(bankroll, 4),
                    drawdown=round(drawdown, 6),
                )
            )

        return BacktestResult(
            config=self.config,
            metrics=calculate_metrics(bets, self.config.initial_bankroll),
            bets=bets,
            equity_curve=equity_curve,
            assumptions=default_assumptions(self.config),
        )

    def select_bets(self, predictions: list[Prediction]) -> list[Prediction]:
        grouped: dict[tuple[str, str, int], list[Prediction]] = {}
        for prediction in predictions:
            probability = probability_for(prediction, self.config.bet_type)
            if probability < self.config.min_probability:
                continue
            if self.config.min_edge is not None:
                edge = prediction.edge if self.config.bet_type == "win" else None
                if edge is not None and edge < self.config.min_edge:
                    continue
            key = (prediction.race_date, prediction.racecourse, prediction.race_no)
            grouped.setdefault(key, []).append(prediction)

        selected: list[Prediction] = []
        for key in sorted(grouped):
            rows = sorted(
                grouped[key],
                key=lambda item: (
                    edge_sort_value(item, self.config.bet_type),
                    probability_for(item, self.config.bet_type),
                ),
                reverse=True,
            )
            selected.extend(rows[: max(1, self.config.top_n_per_race)])
        return selected

    def calculate_stake(self, prediction: Prediction, decimal_odds: float, bankroll: float) -> float:
        if self.config.stake_strategy == "flat":
            return min(self.config.flat_stake, bankroll)
        probability = probability_for(prediction, self.config.bet_type)
        b = decimal_odds - 1
        if b <= 0:
            return 0.0
        kelly = ((b * probability) - (1 - probability)) / b
        if kelly <= 0:
            return 0.0
        fraction = min(kelly * self.config.kelly_fraction, self.config.max_stake_fraction)
        return min(bankroll * fraction, bankroll)


def load_predictions(con: sqlite3.Connection, config: BacktestConfig) -> list[Prediction]:
    if not table_exists(con, "model_predictions"):
        return []
    clauses = ["1 = 1"]
    params: list[Any] = []
    if config.model_name:
        clauses.append("model_name = ?")
        params.append(config.model_name)
    if config.model_version:
        clauses.append("model_version = ?")
        params.append(config.model_version)
    if config.race_date_from:
        clauses.append("race_date >= ?")
        params.append(config.race_date_from)
    if config.race_date_to:
        clauses.append("race_date <= ?")
        params.append(config.race_date_to)
    if config.racecourse:
        clauses.append("racecourse = ?")
        params.append(config.racecourse)

    rows = con.execute(
        f"""
        SELECT payload_json
        FROM model_predictions
        WHERE {' AND '.join(clauses)}
        ORDER BY race_date, racecourse, race_no, horse_code
        """,
        params,
    ).fetchall()
    return [prediction_from_payload(json.loads(row["payload_json"])) for row in rows]


def load_results(con: sqlite3.Connection) -> list[RaceResult]:
    if not table_exists(con, "race_results"):
        return []
    rows = con.execute(
        """
        SELECT race_date, racecourse, race_no, horse_code, horse_no, place, win_odds
        FROM race_results
        """
    ).fetchall()
    return [
        RaceResult(
            race_date=row["race_date"],
            racecourse=row["racecourse"],
            race_no=int(row["race_no"]),
            horse_code=row["horse_code"],
            horse_no=row["horse_no"],
            place=parse_int(row["place"]),
            win_odds=parse_float(row["win_odds"]),
        )
        for row in rows
    ]


def load_dividends(con: sqlite3.Connection) -> list[Dividend]:
    if not table_exists(con, "dividends"):
        return []
    rows = con.execute(
        """
        SELECT race_date, racecourse, race_no, pool, winning_combination, dividend
        FROM dividends
        """
    ).fetchall()
    return [
        Dividend(
            race_date=row["race_date"],
            racecourse=row["racecourse"],
            race_no=int(row["race_no"]),
            pool=str(row["pool"]).upper(),
            winning_combination=str(row["winning_combination"]).strip(),
            dividend=parse_float(row["dividend"]) or 0.0,
        )
        for row in rows
    ]


def prediction_from_payload(payload: dict[str, Any]) -> Prediction:
    return Prediction(
        race_date=payload["raceDate"],
        racecourse=payload["racecourse"],
        race_no=int(payload["raceNo"]),
        horse_code=payload["horseCode"],
        horse_no=str(payload["horseNo"]),
        horse_name=payload["horseName"],
        model_name=payload["modelName"],
        model_version=payload["modelVersion"],
        win_probability=float(payload["winProbability"]),
        place_probability=float(payload["placeProbability"]),
        fair_win_odds=parse_float(payload.get("fairWinOdds")),
        fair_place_odds=parse_float(payload.get("fairPlaceOdds")),
        market_win_probability=parse_float(payload.get("marketWinProbability")),
        edge=parse_float(payload.get("edge")),
        payload=payload,
    )


def index_results(results: list[RaceResult]) -> dict[tuple[str, str, int, str], RaceResult]:
    indexed = {}
    for result in results:
        if result.horse_code:
            indexed[(result.race_date, result.racecourse, result.race_no, result.horse_code)] = result
    return indexed


def index_dividends(dividends: list[Dividend]) -> dict[tuple[str, str | None, int, str, str], float]:
    indexed = {}
    for dividend in dividends:
        indexed[
            (
                dividend.race_date,
                dividend.racecourse,
                dividend.race_no,
                dividend.pool,
                normalize_combination(dividend.winning_combination),
            )
        ] = dividend.dividend / 10.0
    return indexed


def find_result(
    prediction: Prediction,
    result_index: dict[tuple[str, str, int, str], RaceResult],
) -> RaceResult | None:
    return result_index.get((prediction.race_date, prediction.racecourse, prediction.race_no, prediction.horse_code))


def settlement_odds(
    prediction: Prediction,
    bet_type: BetType,
    result: RaceResult,
    dividend_index: dict[tuple[str, str | None, int, str, str], float],
) -> float | None:
    pool = "WIN" if bet_type == "win" else "PLACE"
    key = (
        prediction.race_date,
        prediction.racecourse,
        prediction.race_no,
        pool,
        normalize_combination(prediction.horse_no),
    )
    fallback_key = (
        prediction.race_date,
        None,
        prediction.race_no,
        pool,
        normalize_combination(prediction.horse_no),
    )
    if key in dividend_index:
        return dividend_index[key]
    if fallback_key in dividend_index:
        return dividend_index[fallback_key]
    if bet_type == "win":
        return result.win_odds
    return None


def entry_decimal_odds(prediction: Prediction, bet_type: BetType) -> float | None:
    if bet_type == "win" and prediction.market_win_probability and prediction.market_win_probability > 0:
        return 1 / prediction.market_win_probability
    return None


def is_winning_bet(result: RaceResult, bet_type: BetType) -> bool:
    if result.place is None:
        return False
    if bet_type == "win":
        return result.place == 1
    return result.place <= 3


def calculate_metrics(bets: list[BetRecord], initial_bankroll: float) -> dict[str, float | int | None]:
    turnover = sum(bet.stake for bet in bets)
    profit_loss = sum(bet.profit_loss for bet in bets)
    wins = [bet for bet in bets if bet.is_hit]
    losses = [bet for bet in bets if not bet.is_hit]
    gross_profit = sum(bet.profit_loss for bet in wins)
    gross_loss = abs(sum(bet.profit_loss for bet in losses))
    final_bankroll = initial_bankroll + profit_loss
    return {
        "initialBankroll": round(initial_bankroll, 4),
        "finalBankroll": round(final_bankroll, 4),
        "turnover": round(turnover, 4),
        "profitLoss": round(profit_loss, 4),
        "roi": round(profit_loss / turnover, 6) if turnover else None,
        "hitRate": round(len(wins) / len(bets), 6) if bets else None,
        "maxDrawdown": round(max_drawdown([initial_bankroll, *[bet.bankroll_after for bet in bets]]), 6),
        "profitFactor": round(gross_profit / gross_loss, 6) if gross_loss else None,
        "averageOdds": round(sum((bet.decimal_odds or 0) for bet in bets) / len(bets), 6) if bets else None,
        "betCount": len(bets),
    }


def max_drawdown(values: list[float]) -> float:
    high = values[0] if values else 0.0
    worst = 0.0
    for value in values:
        high = max(high, value)
        if high > 0:
            worst = max(worst, (high - value) / high)
    return worst


def probability_for(prediction: Prediction, bet_type: BetType) -> float:
    return prediction.win_probability if bet_type == "win" else prediction.place_probability


def edge_for(prediction: Prediction, bet_type: BetType, decimal_odds: float | None) -> float | None:
    if bet_type == "win" and prediction.edge is not None:
        return prediction.edge
    if decimal_odds is None or decimal_odds <= 0:
        return None
    return probability_for(prediction, bet_type) - (1 / decimal_odds)


def edge_sort_value(prediction: Prediction, bet_type: BetType) -> float:
    if bet_type == "win":
        return prediction.edge if prediction.edge is not None else -1.0
    return prediction.place_probability


def parse_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def parse_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-", "---"):
            return None
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None


def normalize_combination(value: str) -> str:
    parts = [part.strip() for part in value.replace("+", ",").replace("-", ",").split(",") if part.strip()]
    return ",".join(parts)


def table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def default_assumptions(config: BacktestConfig) -> list[str]:
    assumptions = [
        "每笔投注在赛前按模型输出下注，赛后使用 HKJC 派彩或赛果独赢赔率结算。",
        "下注筛选和 Kelly 注码只使用模型输出中的 market probability，即下注时点可见赔率。",
        "赛后结算使用 HKJC 派彩表；派彩金额按每 10 港元派彩折算为 decimal odds，payout 包含本金。",
        "暂未计入交易成本、滑点、注额上限、赔率成交失败和盘口停牌。",
        "同一场最多下注 top_n_per_race 个候选，按 edge 和模型概率排序。",
    ]
    if config.bet_type == "place":
        assumptions.append("位置投注使用 PLACE 派彩结算；若缺少赛前位置市场概率，下注赔率仅用于结算，不用于筛选 edge。")
    if config.stake_strategy == "fractional_kelly":
        assumptions.append("分数 Kelly 使用下注时点可见赔率估算下注比例；缺少该赔率时会退回结算赔率并降低可信度。")
    return assumptions


def result_to_dict(result: BacktestResult) -> dict[str, Any]:
    return {
        "config": asdict(result.config),
        "metrics": result.metrics,
        "bets": [asdict(bet) for bet in result.bets],
        "equityCurve": [asdict(point) for point in result.equity_curve],
        "assumptions": result.assumptions,
    }
