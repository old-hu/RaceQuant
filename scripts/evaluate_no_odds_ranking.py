from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate no-odds model ranking quality without settlement odds.")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--predictions", type=Path, default=Path("frontend/public/data/baseline_predictions.json"))
    parser.add_argument("--output", type=Path, default=Path("data/reports/no_odds_model_ranking_latest.json"))
    parser.add_argument("--artifact-json", type=Path, help="Optional model metadata JSON produced by train_baseline_model.py.")
    args = parser.parse_args()

    predictions = json.loads(args.predictions.read_text(encoding="utf-8")) if args.predictions.exists() else []
    labels, race_metadata = load_result_context(args.db)
    artifact = json.loads(args.artifact_json.read_text(encoding="utf-8")) if args.artifact_json and args.artifact_json.exists() else None
    report = evaluate(predictions, labels, race_metadata, artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    print(f"Wrote ranking report to {args.output}")


def load_result_context(
    db_path: Path,
) -> tuple[dict[tuple[str, str, int, str], int], dict[tuple[str, str, int], dict[str, Any]]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        result_rows = con.execute(
            """
            SELECT race_date, racecourse, race_no, horse_code, place
            FROM race_results
            WHERE horse_code IS NOT NULL
            """
        ).fetchall()
        metadata_rows = con.execute(
            """
            SELECT race_date, racecourse, race_no, distance_m, surface, race_class
            FROM race_metadata
            """
        ).fetchall()
    finally:
        con.close()
    labels = {}
    for row in result_rows:
        if str(row["place"]).isdigit():
            labels[(row["race_date"], row["racecourse"], int(row["race_no"]), row["horse_code"])] = int(row["place"])
    metadata = {
        (row["race_date"], row["racecourse"], int(row["race_no"])): {
            "distanceM": row["distance_m"],
            "surface": row["surface"],
            "raceClass": row["race_class"],
        }
        for row in metadata_rows
    }
    return labels, metadata


def evaluate(
    predictions: list[dict[str, Any]],
    labels: dict[tuple[str, str, int, str], int],
    race_metadata: dict[tuple[str, str, int], dict[str, Any]],
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_race: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for item in predictions:
        by_race[(item["raceDate"], item["racecourse"], int(item["raceNo"]))].append(item)

    overall = RankingAccumulator()
    by_year: dict[str, RankingAccumulator] = defaultdict(RankingAccumulator)
    by_racecourse: dict[str, RankingAccumulator] = defaultdict(RankingAccumulator)
    by_distance_band: dict[str, RankingAccumulator] = defaultdict(RankingAccumulator)
    win_bins = CalibrationBins()
    place_bins = CalibrationBins()

    for race_key, rows in by_race.items():
        ranked = sorted(rows, key=lambda item: item.get("winProbability") or 0.0, reverse=True)
        if not ranked:
            continue
        race_date, racecourse, _race_no = race_key
        year = race_date[:4]
        metadata = race_metadata.get(race_key, {})
        distance_band = distance_bucket(metadata.get("distanceM"))

        winner = next((item for item in ranked if finish_place(item, labels) == 1), None)
        winner_rank = ranked.index(winner) + 1 if winner else None
        for accumulator in [overall, by_year[year], by_racecourse[racecourse], by_distance_band[distance_band]]:
            accumulator.add_race(ranked, winner_rank, labels)

        for item in ranked:
            place = finish_place(item, labels)
            if place is None:
                continue
            win_bins.add(item.get("winProbability"), place == 1)
            place_bins.add(item.get("placeProbability"), place <= 3)

    prediction_meta = prediction_metadata(predictions)
    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "predictions joined to race_results labels",
        "model": artifact_summary(artifact) or prediction_meta,
        "metrics": overall.metrics(),
        "segments": {
            "byYear": accumulator_map(by_year),
            "byRacecourse": accumulator_map(by_racecourse),
            "byDistanceBand": accumulator_map(by_distance_band),
        },
        "calibration": {
            "winProbability": win_bins.report(),
            "placeProbability": place_bins.report(),
        },
    }


def finish_place(item: dict[str, Any], labels: dict[tuple[str, str, int, str], int]) -> int | None:
    key = (item["raceDate"], item["racecourse"], int(item["raceNo"]), item["horseCode"])
    return labels.get(key)


def is_place(item: dict[str, Any], labels: dict[tuple[str, str, int, str], int]) -> bool:
    place = finish_place(item, labels)
    return place is not None and place <= 3


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


class RankingAccumulator:
    def __init__(self) -> None:
        self.race_count = 0
        self.runner_count = 0
        self.labelled_race_count = 0
        self.top1_win_hits = 0
        self.top1_place_hits = 0
        self.top3_contains_winner = 0
        self.top3_place_hits = 0
        self.winner_ranks: list[int] = []

    def add_race(
        self,
        ranked: list[dict[str, Any]],
        winner_rank: int | None,
        labels: dict[tuple[str, str, int, str], int],
    ) -> None:
        self.race_count += 1
        self.runner_count += len(ranked)
        self.top1_place_hits += int(is_place(ranked[0], labels))
        self.top3_place_hits += sum(1 for item in ranked[:3] if is_place(item, labels))
        if winner_rank is None:
            return
        self.labelled_race_count += 1
        self.winner_ranks.append(winner_rank)
        self.top1_win_hits += int(winner_rank == 1)
        self.top3_contains_winner += int(winner_rank <= 3)

    def metrics(self) -> dict[str, Any]:
        return {
            "race_count": self.race_count,
            "runner_count": self.runner_count,
            "labelled_race_count": self.labelled_race_count,
            "top1_win_hits": self.top1_win_hits,
            "top1_place_hits": self.top1_place_hits,
            "top3_contains_winner": self.top3_contains_winner,
            "top3_place_hits": self.top3_place_hits,
            "avg_winner_rank": (sum(self.winner_ranks) / len(self.winner_ranks)) if self.winner_ranks else None,
            "top1_win_rate": ratio(self.top1_win_hits, self.labelled_race_count),
            "top1_place_rate": ratio(self.top1_place_hits, self.race_count),
            "top3_winner_coverage": ratio(self.top3_contains_winner, self.labelled_race_count),
            "top3_place_hit_rate_per_slot": ratio(self.top3_place_hits, self.race_count * 3),
        }


class CalibrationBins:
    def __init__(self, bucket_count: int = 10) -> None:
        self.bucket_count = bucket_count
        self.buckets = [{"count": 0, "prob_sum": 0.0, "hit_sum": 0} for _ in range(bucket_count)]

    def add(self, probability: Any, hit: bool) -> None:
        if probability is None:
            return
        value = max(0.0, min(1.0, float(probability)))
        index = min(int(value * self.bucket_count), self.bucket_count - 1)
        bucket = self.buckets[index]
        bucket["count"] += 1
        bucket["prob_sum"] += value
        bucket["hit_sum"] += int(hit)

    def report(self) -> list[dict[str, Any]]:
        report = []
        for index, bucket in enumerate(self.buckets):
            low = index / self.bucket_count
            high = (index + 1) / self.bucket_count
            count = int(bucket["count"])
            report.append(
                {
                    "bucket": f"{low:.1f}-{high:.1f}",
                    "count": count,
                    "avgPredictedProbability": ratio(bucket["prob_sum"], count),
                    "observedHitRate": ratio(bucket["hit_sum"], count),
                }
            )
        return report


def accumulator_map(accumulators: dict[str, RankingAccumulator]) -> dict[str, dict[str, Any]]:
    return {key: accumulators[key].metrics() for key in sorted(accumulators)}


def distance_bucket(distance: Any) -> str:
    if distance is None:
        return "unknown"
    value = int(distance)
    if value <= 1200:
        return "<=1200"
    if value <= 1600:
        return "1201-1600"
    if value <= 2000:
        return "1601-2000"
    return ">2000"


def prediction_metadata(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    if not predictions:
        return {}
    first = predictions[0]
    return {
        "modelName": first.get("modelName"),
        "modelVersion": first.get("modelVersion"),
        "trainingDatasetVersion": first.get("trainingDatasetVersion"),
        "featureVersion": first.get("featureVersion"),
        "oddsMode": first.get("oddsMode"),
        "dataBuildId": first.get("dataBuildId"),
    }


def artifact_summary(artifact: dict[str, Any] | None) -> dict[str, Any] | None:
    if not artifact:
        return None
    return {
        "modelName": artifact.get("model_name"),
        "modelVersion": artifact.get("model_version"),
        "oddsMode": artifact.get("odds_mode"),
        "trainingDatasetVersion": artifact.get("training_dataset_version"),
        "featureVersion": artifact.get("feature_version"),
        "dataBuildId": artifact.get("data_build_id"),
        "rowCount": artifact.get("row_count"),
        "trainingMetrics": artifact.get("metrics"),
        "artifactPath": artifact.get("artifact_path"),
    }


if __name__ == "__main__":
    main()
