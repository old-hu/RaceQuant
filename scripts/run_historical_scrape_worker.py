from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from hkjc_structured_store import (
    mark_job,
    missing_horse_history_codes,
    next_pending_job,
    parse_change_outputs,
    parse_horse_history_outputs,
    parse_job_outputs,
    race_day_has_core_data,
    set_raw_dir,
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


def run_next_job(
    max_race_no: int,
    report_dir: Path,
    db_path: Path = Path("data/processed/hkjc_structured.sqlite"),
    raw_dir: Path = Path("data/raw/hkjc"),
    max_horse_histories: int = 20,
) -> None:
    set_raw_dir(raw_dir)
    job = next_pending_job(db_path)
    if not job:
        print("No pending historical scrape jobs.", flush=True)
        return

    job_id = int(job["id"])
    race_date = job["race_date"]
    racecourse = job["racecourse"]
    print(f"Running historical job #{job_id}: {race_date} {racecourse}", flush=True)
    mark_job(job_id, "running", db_path=db_path)

    results = []
    try:
        results.extend(run_meeting_commands(race_date, racecourse, raw_dir))
        for race_no in range(1, max_race_no + 1):
            results.extend(run_race_commands(race_date, racecourse, race_no, raw_dir))

        failed = [result for result in results if result["returncode"] != 0]
        structured = parse_job_outputs(race_date, racecourse, max_race_no=max_race_no, db_path=db_path)
        structured.update(parse_change_outputs(db_path=db_path))
        if failed:
            error = summarize_failures(failed)
            structured["failed_commands"] = len(failed)
            status = "done_with_warnings" if race_day_has_core_data(race_date, racecourse, db_path=db_path) else "failed"
            mark_job(job_id, status, error, db_path=db_path)
        else:
            horse_codes = (
                missing_horse_history_codes(db_path=db_path, raw_dir=raw_dir, limit=max_horse_histories)
                if max_horse_histories > 0
                else []
            )
            if horse_codes:
                structured["horse_history_scrape_commands"] = len(horse_codes)
                for horse_code in horse_codes:
                    results.append(run_horse_history_command(horse_code, raw_dir))
            structured.update(parse_horse_history_outputs(db_path=db_path))
            mark_job(job_id, "done", db_path=db_path)
        results.append({"structured": structured})
        run_command([sys.executable, "scripts/export_scrape_summary.py", "--raw-dir", str(raw_dir)])
        run_command([sys.executable, "scripts/export_structured_data.py", "--db", str(db_path)])
    except Exception as exc:
        mark_job(job_id, "failed", str(exc), db_path=db_path)
        results.append({"exception": str(exc)})

    write_report(report_dir, job_id, race_date, racecourse, results)


def run_meeting_commands(race_date: str, racecourse: str, raw_dir: Path) -> list[dict[str, object]]:
    commands = [
        ["scripts/scrape_changes.py", "--race-date", race_date, "--output-dir", str(raw_dir)],
        ["scripts/scrape_dividends.py", "--race-date", race_date, "--output-dir", str(raw_dir)],
        ["scripts/scrape_race_meeting.py", "--race-date", race_date, "--racecourse", racecourse, "--output-dir", str(raw_dir)],
        ["scripts/scrape_entries.py", "--race-date", race_date, "--racecourse", racecourse, "--output-dir", str(raw_dir)],
    ]
    return [run_command([sys.executable, *command]) for command in commands]


def run_race_commands(race_date: str, racecourse: str, race_no: int, raw_dir: Path) -> list[dict[str, object]]:
    commands = [
        [
            "scripts/scrape_race_cards.py",
            "--race-date",
            race_date,
            "--racecourse",
            racecourse,
            "--race-no",
            str(race_no),
            "--output-dir",
            str(raw_dir),
        ],
        [
            "scripts/scrape_results.py",
            "--race-date",
            race_date,
            "--racecourse",
            racecourse,
            "--race-no",
            str(race_no),
            "--output-dir",
            str(raw_dir),
        ],
    ]
    return [run_command([sys.executable, *command]) for command in commands]


def run_horse_history_command(horse_code: str, raw_dir: Path) -> dict[str, object]:
    return run_command(
        [
            sys.executable,
            "scripts/scrape_horse_history.py",
            "--horse-no",
            horse_code,
            "--output-dir",
            str(raw_dir),
        ]
    )


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


def summarize_failures(failed: list[dict[str, object]]) -> str:
    parts = []
    for item in failed[:10]:
        command = item.get("command")
        command_text = " ".join(str(part) for part in command) if isinstance(command, list) else str(command)
        stderr = str(item.get("stderr") or "").strip().splitlines()
        stdout = str(item.get("stdout") or "").strip().splitlines()
        detail = stderr[-1] if stderr else (stdout[-1] if stdout else "command failed")
        parts.append(f"{command_text}: {detail[:300]}")
    suffix = f"; +{len(failed) - 10} more failed commands" if len(failed) > 10 else ""
    return "; ".join(parts)[:2000] + suffix


def main() -> None:
    parser = argparse.ArgumentParser(description="每次执行一个未完成赛日的历史全量爬取工人。")
    parser.add_argument("--interval-seconds", type=int, default=5, help="定时执行间隔，默认 5 秒。")
    parser.add_argument("--max-race-no", type=int, default=12, help="每个赛日最多尝试场次数。")
    parser.add_argument("--once", action="store_true", help="只执行一个未完成任务。")
    parser.add_argument("--report-dir", type=Path, default=Path("data/reports"))
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/hkjc"))
    parser.add_argument("--max-horse-histories", type=int, default=20, help="Maximum missing horse history pages to scrape after each race-day job. 0 disables this step.")
    args = parser.parse_args()

    if args.once:
        run_next_job(args.max_race_no, args.report_dir, args.db, args.raw_dir, args.max_horse_histories)
        return

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        run_next_job,
        "interval",
        seconds=args.interval_seconds,
        next_run_time=datetime.now(),
        args=[args.max_race_no, args.report_dir, args.db, args.raw_dir, args.max_horse_histories],
        id="hkjc_history_worker",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    print(f"Historical scrape worker started. interval={args.interval_seconds} seconds", flush=True)
    scheduler.start()


if __name__ == "__main__":
    main()
