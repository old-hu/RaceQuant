from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the no-odds training pipeline only after official backfill is complete.")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/hkjc"))
    parser.add_argument("--odds-db", type=Path, default=Path("data/processed/legacy_horse_odds.sqlite"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("models/baseline"))
    parser.add_argument("--predictions-output", type=Path, default=Path("frontend/public/data/baseline_predictions.json"))
    parser.add_argument("--report", type=Path, default=Path("data/reports/train_when_ready_latest.json"))
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--max-race-no", type=int, default=12)
    parser.add_argument("--force", action="store_true", help="Run even if scrape_jobs still have pending/running/failed work.")
    parser.add_argument("--dry-run", action="store_true", help="Only report readiness; do not run the pipeline.")
    args = parser.parse_args()

    status = readiness_status(args.db)
    report: dict[str, Any] = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ready": status["ready"],
        "forced": args.force,
        "status": status,
        "commands": [],
    }
    if args.dry_run or (not args.force and not status["ready"]):
        write_report(args.report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    data_build_id = f"official_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    commands = [
        [
            sys.executable,
            "scripts/build_local_data.py",
            "--source",
            "raw",
            "--raw-dir",
            str(args.raw_dir),
            "--structured-db",
            str(args.db),
            "--odds-db",
            str(args.odds_db),
            "--max-race-no",
            str(args.max_race_no),
        ],
        [
            sys.executable,
            "scripts/build_no_odds_training_dataset.py",
            "--db",
            str(args.db),
            "--limit",
            str(args.limit),
        ],
        [
            sys.executable,
            "scripts/train_baseline_model.py",
            "--db",
            str(args.db),
            "--artifact-dir",
            str(args.artifact_dir),
            "--odds-mode",
            "none",
            "--training-dataset-version",
            "official_raw_no_odds",
            "--feature-version",
            "runner_features_v2_horse_form",
            "--data-build-id",
            data_build_id,
            "--limit",
            str(args.limit),
        ],
    ]
    for command in commands:
        report["commands"].append(run_command(command))
        if report["commands"][-1]["returncode"] != 0:
            write_report(args.report, report)
            raise SystemExit(1)

    artifact_path = latest_artifact(args.artifact_dir)
    post_commands = [
        [
            sys.executable,
            "scripts/generate_predictions.py",
            "--db",
            str(args.db),
            "--artifact",
            str(artifact_path),
            "--output",
            str(args.predictions_output),
            "--write-db",
            "--limit",
            str(args.limit),
        ],
        [
            sys.executable,
            "scripts/evaluate_no_odds_ranking.py",
            "--db",
            str(args.db),
            "--predictions",
            str(args.predictions_output),
            "--artifact-json",
            str(artifact_path.with_suffix(".json")),
        ],
        [sys.executable, "scripts/export_structured_data.py", "--db", str(args.db)],
        [sys.executable, "scripts/export_scrape_summary.py", "--raw-dir", str(args.raw_dir)],
    ]
    report["artifactPath"] = str(artifact_path)
    for command in post_commands:
        report["commands"].append(run_command(command))
        if report["commands"][-1]["returncode"] != 0:
            write_report(args.report, report)
            raise SystemExit(1)

    report["completed"] = True
    write_report(args.report, report)
    print(json.dumps({"completed": True, "artifactPath": str(artifact_path), "report": str(args.report)}, ensure_ascii=False, indent=2))


def readiness_status(db_path: Path) -> dict[str, Any]:
    con = sqlite3.connect(db_path, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        statuses = dict(con.execute("SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status").fetchall())
        active = sum(int(statuses.get(status, 0)) for status in ["pending", "running", "failed"])
        ranges = {
            "officialRaceDays": dict(con.execute("SELECT MIN(race_date) min_date, MAX(race_date) max_date, COUNT(*) count FROM official_race_days").fetchone()),
            "raceResults": dict(con.execute("SELECT MIN(race_date) min_date, MAX(race_date) max_date, COUNT(*) count FROM race_results").fetchone()),
            "horseFormRecords": dict(con.execute("SELECT COUNT(*) count FROM horse_form_records").fetchone()),
        }
    finally:
        con.close()
    return {
        "ready": active == 0,
        "blockingJobCount": active,
        "scrapeJobStatus": statuses,
        "ranges": ranges,
    }


def latest_artifact(artifact_dir: Path) -> Path:
    artifacts = sorted(artifact_dir.glob("no_odds_*.pkl"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not artifacts:
        raise FileNotFoundError(f"No no_odds artifact found in {artifact_dir}")
    return artifacts[0]


def run_command(command: list[str]) -> dict[str, Any]:
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "command": command,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
