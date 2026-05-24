from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from hkjc_structured_store import (
    mark_job,
    next_pending_job,
    parse_change_outputs,
    parse_horse_history_outputs,
    parse_job_outputs,
)


def run_command(command: list[str]) -> dict[str, object]:
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "command": command,
        "started_at": started_at,
        "finished_at": finished_at,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def run_next_job(max_race_no: int, report_dir: Path) -> None:
    job = next_pending_job()
    if not job:
        print("No pending historical scrape jobs.", flush=True)
        return

    job_id = int(job["id"])
    race_date = job["race_date"]
    racecourse = job["racecourse"]
    print(f"Running historical job #{job_id}: {race_date} {racecourse}", flush=True)
    mark_job(job_id, "running")

    results = []
    try:
        results.extend(run_meeting_commands(race_date, racecourse))
        for race_no in range(1, max_race_no + 1):
            results.extend(run_race_commands(race_date, racecourse, race_no))

        failed = [result for result in results if result["returncode"] != 0]
        if failed:
            error = "; ".join(str(item["stderr"])[:300] for item in failed)
            mark_job(job_id, "failed", error or "command failed")
        else:
            structured = parse_job_outputs(race_date, racecourse, max_race_no=max_race_no)
            structured.update(parse_change_outputs())
            structured.update(parse_horse_history_outputs())
            mark_job(job_id, "done")
            results.append({"structured": structured})
            run_command([sys.executable, "scripts/export_scrape_summary.py"])
            run_command([sys.executable, "scripts/export_structured_data.py"])
    except Exception as exc:
        mark_job(job_id, "failed", str(exc))
        results.append({"exception": str(exc)})

    write_report(report_dir, job_id, race_date, racecourse, results)


def run_meeting_commands(race_date: str, racecourse: str) -> list[dict[str, object]]:
    commands = [
        ["scripts/scrape_changes.py", "--race-date", race_date],
        ["scripts/scrape_dividends.py", "--race-date", race_date],
        ["scripts/scrape_race_meeting.py", "--race-date", race_date, "--racecourse", racecourse],
        ["scripts/scrape_entries.py", "--race-date", race_date, "--racecourse", racecourse],
    ]
    return [run_command([sys.executable, *command]) for command in commands]


def run_race_commands(race_date: str, racecourse: str, race_no: int) -> list[dict[str, object]]:
    commands = [
        [
            "scripts/scrape_race_cards.py",
            "--race-date",
            race_date,
            "--racecourse",
            racecourse,
            "--race-no",
            str(race_no),
        ],
        [
            "scripts/scrape_results.py",
            "--race-date",
            race_date,
            "--racecourse",
            racecourse,
            "--race-no",
            str(race_no),
        ],
    ]
    return [run_command([sys.executable, *command]) for command in commands]


def write_report(
    report_dir: Path,
    job_id: int,
    race_date: str,
    racecourse: str,
    results: list[dict[str, object]],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"hkjc_history_job_{run_id}_{job_id}.json"
    report_path.write_text(
        json.dumps(
            {
                "job_id": job_id,
                "race_date": race_date,
                "racecourse": racecourse,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {report_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="每次执行一个未完成赛日的历史全量爬取工人。")
    parser.add_argument("--interval-seconds", type=int, default=5, help="定时执行间隔，默认 5 秒。")
    parser.add_argument("--max-race-no", type=int, default=12, help="每个赛日最多尝试场次数。")
    parser.add_argument("--once", action="store_true", help="只执行一个未完成任务。")
    parser.add_argument("--report-dir", type=Path, default=Path("data/reports"))
    args = parser.parse_args()

    if args.once:
        run_next_job(args.max_race_no, args.report_dir)
        return

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        run_next_job,
        "interval",
        seconds=args.interval_seconds,
        next_run_time=datetime.now(),
        args=[args.max_race_no, args.report_dir],
        id="hkjc_history_worker",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    print(f"Historical scrape worker started. interval={args.interval_seconds} seconds", flush=True)
    scheduler.start()


if __name__ == "__main__":
    main()
