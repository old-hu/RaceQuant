from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


BetType = Literal["win", "place"]
StakeStrategy = Literal["flat", "fractional_kelly"]
CandidateStatus = Literal["selected", "filtered", "not_selected"]
BACKTEST_VERSION = "backtest_engine_v1"


@dataclass(frozen=True)
class BacktestConfig:
    bet_type: BetType = "win"
    stake_strategy: StakeStrategy = "flat"
    initial_bankroll: float = 10_000.0
    flat_stake: float = 10.0
    kelly_fraction: float = 0.25
    max_stake_fraction: float = 0.02
    transaction_cost_rate: float = 0.0
    slippage_rate: float = 0.0
    min_probability: float = 0.0
    min_edge: float | None = 0.03
    safety_margin_by_bet_type: dict[str, float | None] = field(default_factory=dict)
    min_probability_by_bet_type: dict[str, float] = field(default_factory=dict)
    min_pool_size: float = 0.0
    min_pool_size_by_bet_type: dict[str, float] = field(default_factory=dict)
    min_odds_by_bet_type: dict[str, float] = field(default_factory=dict)
    max_odds_by_bet_type: dict[str, float] = field(default_factory=dict)
    top_n_per_race: int = 1
    model_name: str | None = None
    model_version: str | None = None
    training_dataset_version: str | None = None
    feature_version: str | None = None
    odds_mode: str | None = None
    data_build_id: str | None = None
    backtest_version: str = BACKTEST_VERSION
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
    market_place_probability: float | None = None
    edge: float | None = None
    training_dataset_version: str | None = None
    feature_version: str | None = None
    odds_mode: str | None = None
    data_build_id: str | None = None
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


@dataclass
class CandidateExplanation:
    race_date: str
    racecourse: str
    race_no: int
    horse_code: str
    horse_no: str
    horse_name: str
    bet_type: BetType
    status: CandidateStatus
    filter_reason: str | None
    model_probability: float
    market_probability: float | None
    fair_odds: float | None
    entry_odds: float | None
    edge: float | None
    pool_size: float | None
    feature_contributions: dict[str, float]


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
    candidate_explanations: list[CandidateExplanation]
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
        candidates, candidate_explanations = self.evaluate_predictions(predictions)
        explanation_index = {candidate_key(item): item for item in candidate_explanations}
        bankroll = self.config.initial_bankroll
        high_watermark = bankroll
        bets: list[BetRecord] = []
        equity_curve: list[EquityPoint] = []

        for candidate in candidates:
            explanation = explanation_index.get(candidate_key(candidate))
            result = find_result(candidate, result_index)
            if result is None:
                mark_filtered(explanation, "missing_result")
                continue
            entry_odds = entry_decimal_odds(candidate, self.config.bet_type)
            settlement_decimal_odds = settlement_odds(candidate, self.config.bet_type, result, dividend_index)
            if settlement_decimal_odds is None or settlement_decimal_odds <= 1:
                mark_filtered(explanation, "missing_or_invalid_settlement_odds")
                continue
            effective_entry_odds = apply_slippage(entry_odds or settlement_decimal_odds, self.config.slippage_rate)
            effective_settlement_odds = apply_slippage(settlement_decimal_odds, self.config.slippage_rate)
            if effective_entry_odds <= 1 or effective_settlement_odds <= 1:
                mark_filtered(explanation, "invalid_odds_after_slippage")
                continue
            stake = self.calculate_stake(candidate, effective_entry_odds, bankroll)
            if stake <= 0:
                mark_filtered(explanation, "stake_not_positive")
                continue

            is_hit = is_winning_bet(result, self.config.bet_type)
            transaction_cost = stake * self.config.transaction_cost_rate
            payout = stake * effective_settlement_odds if is_hit else 0.0
            profit_loss = payout - stake - transaction_cost
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
                    decimal_odds=round(effective_entry_odds, 4),
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
            candidate_explanations=candidate_explanations,
            assumptions=default_assumptions(self.config),
        )

    def select_bets(self, predictions: list[Prediction]) -> list[Prediction]:
        selected, _ = self.evaluate_predictions(predictions)
        return selected

    def evaluate_predictions(self, predictions: list[Prediction]) -> tuple[list[Prediction], list[CandidateExplanation]]:
        grouped: dict[tuple[str, str, int], list[Prediction]] = {}
        explanations: dict[tuple[str, str, int, str], CandidateExplanation] = {}
        for prediction in predictions:
            entry_odds = entry_decimal_odds(prediction, self.config.bet_type)
            explanation = candidate_explanation(prediction, self.config.bet_type)
            explanations[candidate_key(prediction)] = explanation
            filter_reason = odds_filter_reason(entry_odds, self.config.bet_type, self.config)
            if filter_reason:
                mark_filtered(explanation, filter_reason)
                continue
            filter_reason = liquidity_filter_reason(prediction, self.config.bet_type, self.config)
            if filter_reason:
                mark_filtered(explanation, filter_reason)
                continue
            probability = probability_for(prediction, self.config.bet_type)
            if probability < min_probability_for(self.config, self.config.bet_type):
                mark_filtered(explanation, "below_min_probability")
                continue
            safety_margin = safety_margin_for(self.config, self.config.bet_type)
            if safety_margin is not None:
                edge = edge_for(prediction, self.config.bet_type, entry_odds)
                if edge is None or edge < safety_margin:
                    mark_filtered(explanation, "below_safety_margin")
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
            top_n = max(1, self.config.top_n_per_race)
            selected.extend(rows[:top_n])
            for item in rows[:top_n]:
                explanations[candidate_key(item)].status = "selected"
            for item in rows[top_n:]:
                mark_not_selected(explanations[candidate_key(item)], "outside_top_n_per_race")
        return selected, list(explanations.values())

    def calculate_stake(self, prediction: Prediction, decimal_odds: float, bankroll: float) -> float:
        max_stake = bankroll * self.config.max_stake_fraction if self.config.max_stake_fraction > 0 else bankroll
        if self.config.stake_strategy == "flat":
            return min(self.config.flat_stake, max_stake, bankroll)
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
        training_dataset_version=payload.get("trainingDatasetVersion"),
        feature_version=payload.get("featureVersion"),
        odds_mode=payload.get("oddsMode"),
        data_build_id=payload.get("dataBuildId"),
        win_probability=float(payload["winProbability"]),
        place_probability=float(payload["placeProbability"]),
        fair_win_odds=parse_float(payload.get("fairWinOdds")),
        fair_place_odds=parse_float(payload.get("fairPlaceOdds")),
        market_win_probability=parse_float(payload.get("marketWinProbability")),
        market_place_probability=parse_float(payload.get("marketPlaceProbability")),
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
    if bet_type == "place" and prediction.market_place_probability and prediction.market_place_probability > 0:
        return 1 / prediction.market_place_probability
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
    edge = edge_for(prediction, bet_type, entry_decimal_odds(prediction, bet_type))
    return edge if edge is not None else prediction.place_probability


def safety_margin_for(config: BacktestConfig, bet_type: BetType) -> float | None:
    return config.safety_margin_by_bet_type.get(bet_type, config.min_edge)


def min_probability_for(config: BacktestConfig, bet_type: BetType) -> float:
    return config.min_probability_by_bet_type.get(bet_type, config.min_probability)


def min_pool_size_for(config: BacktestConfig, bet_type: BetType) -> float:
    return config.min_pool_size_by_bet_type.get(bet_type, config.min_pool_size)


def odds_filter_reason(decimal_odds: float | None, bet_type: BetType, config: BacktestConfig) -> str | None:
    if decimal_odds is None:
        return None
    min_odds = config.min_odds_by_bet_type.get(bet_type)
    max_odds = config.max_odds_by_bet_type.get(bet_type)
    if min_odds is not None and decimal_odds < min_odds:
        return "below_min_odds"
    if max_odds is not None and decimal_odds > max_odds:
        return "above_max_odds"
    return None


def passes_odds_filter(decimal_odds: float | None, bet_type: BetType, config: BacktestConfig) -> bool:
    return odds_filter_reason(decimal_odds, bet_type, config) is None


def liquidity_filter_reason(prediction: Prediction, bet_type: BetType, config: BacktestConfig) -> str | None:
    required_pool_size = min_pool_size_for(config, bet_type)
    if required_pool_size <= 0:
        return None
    pool_size = pool_size_for(prediction, bet_type)
    if pool_size is None:
        return "missing_pool_size"
    if pool_size < required_pool_size:
        return "below_min_pool_size"
    return None


def passes_liquidity_filter(prediction: Prediction, bet_type: BetType, config: BacktestConfig) -> bool:
    return liquidity_filter_reason(prediction, bet_type, config) is None


def pool_size_for(prediction: Prediction, bet_type: BetType) -> float | None:
    keys = (
        ("marketWinPoolSize", "winPoolSize", "poolSize", "liquidity")
        if bet_type == "win"
        else ("marketPlacePoolSize", "placePoolSize", "poolSize", "liquidity")
    )
    for key in keys:
        value = parse_float(prediction.payload.get(key))
        if value is not None:
            return value
    return None


def candidate_explanation(prediction: Prediction, bet_type: BetType) -> CandidateExplanation:
    entry_odds = entry_decimal_odds(prediction, bet_type)
    return CandidateExplanation(
        race_date=prediction.race_date,
        racecourse=prediction.racecourse,
        race_no=prediction.race_no,
        horse_code=prediction.horse_code,
        horse_no=prediction.horse_no,
        horse_name=prediction.horse_name,
        bet_type=bet_type,
        status="filtered",
        filter_reason=None,
        model_probability=round(probability_for(prediction, bet_type), 6),
        market_probability=round(1 / entry_odds, 6) if entry_odds and entry_odds > 0 else None,
        fair_odds=fair_odds_for(prediction, bet_type),
        entry_odds=round(entry_odds, 6) if entry_odds is not None else None,
        edge=round(edge_for(prediction, bet_type, entry_odds), 6) if edge_for(prediction, bet_type, entry_odds) is not None else None,
        pool_size=pool_size_for(prediction, bet_type),
        feature_contributions=feature_contributions_for(prediction),
    )


def candidate_key(prediction: Prediction | CandidateExplanation) -> tuple[str, str, int, str]:
    return (prediction.race_date, prediction.racecourse, prediction.race_no, prediction.horse_code)


def fair_odds_for(prediction: Prediction, bet_type: BetType) -> float | None:
    value = prediction.fair_win_odds if bet_type == "win" else prediction.fair_place_odds
    return round(value, 6) if value is not None else None


def feature_contributions_for(prediction: Prediction) -> dict[str, float]:
    raw = (
        prediction.payload.get("featureContributions")
        or prediction.payload.get("feature_contributions")
        or prediction.payload.get("topFeatureContributions")
        or {}
    )
    if isinstance(raw, dict):
        return {
            str(key): float(value)
            for key, value in sorted(raw.items(), key=lambda item: abs(parse_float(item[1]) or 0.0), reverse=True)[:5]
            if parse_float(value) is not None
        }
    if isinstance(raw, list):
        items: list[tuple[str, float]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("feature") or item.get("name")
            value = parse_float(item.get("contribution") or item.get("value"))
            if name and value is not None:
                items.append((str(name), value))
        return dict(sorted(items, key=lambda item: abs(item[1]), reverse=True)[:5])
    return {}


def mark_filtered(explanation: CandidateExplanation | None, reason: str) -> None:
    if explanation is not None:
        explanation.status = "filtered"
        explanation.filter_reason = reason


def mark_not_selected(explanation: CandidateExplanation | None, reason: str) -> None:
    if explanation is not None:
        explanation.status = "not_selected"
        explanation.filter_reason = reason


def apply_slippage(decimal_odds: float, slippage_rate: float) -> float:
    if slippage_rate <= 0:
        return decimal_odds
    return max(1.0, decimal_odds * (1 - slippage_rate))


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
        "缺少结算赔率、结算赔率无效或滑点后赔率不高于 1 时，该候选会被跳过。",
        "同一场最多下注 top_n_per_race 个候选，按对应投注类型的 edge 和模型概率排序。",
        f"单笔注额不超过当前资金的 {config.max_stake_fraction:.2%}。",
    ]
    assumptions.append(f"{config.bet_type} 最低模型概率为 {min_probability_for(config, config.bet_type):.2%}。")
    assumptions.append(f"回测版本：{config.backtest_version}。")
    if config.model_version:
        assumptions.append(f"模型版本：{config.model_version}。")
    if config.training_dataset_version:
        assumptions.append(f"训练数据版本：{config.training_dataset_version}。")
    if config.feature_version:
        assumptions.append(f"特征版本：{config.feature_version}。")
    if config.odds_mode:
        assumptions.append(f"赔率模式：{config.odds_mode}。")
    if config.data_build_id:
        assumptions.append(f"数据构建版本：{config.data_build_id}。")
    safety_margin = safety_margin_for(config, config.bet_type)
    if safety_margin is not None:
        assumptions.append(f"{config.bet_type} safety margin 为 {safety_margin:.2%}。")
    min_pool_size = min_pool_size_for(config, config.bet_type)
    if min_pool_size > 0:
        assumptions.append(f"{config.bet_type} 候选需要可见 pool size 不低于 {min_pool_size:g}。")
    if config.transaction_cost_rate > 0:
        assumptions.append(f"每笔投注按注额扣除 {config.transaction_cost_rate:.2%} 交易成本。")
    if config.slippage_rate > 0:
        assumptions.append(f"结算赔率和 Kelly 估算赔率按 {config.slippage_rate:.2%} 滑点下调。")
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
        "candidateExplanations": [asdict(explanation) for explanation in result.candidate_explanations],
        "assumptions": result.assumptions,
    }
