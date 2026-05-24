from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler


@dataclass(frozen=True)
class ScrapeScope:
    race_date: str
    racecourse: str
    race_nos: list[int]
    horse_nos: list[str]


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


def scrape_scope(scope: ScrapeScope) -> list[dict[str, object]]:
    results = []

    meeting_commands = [
        ["scripts/scrape_race_meeting.py", "--race-date", scope.race_date, "--racecourse", scope.racecourse],
        ["scripts/scrape_entries.py", "--race-date", scope.race_date, "--racecourse", scope.racecourse],
    ]
    for command in meeting_commands:
        results.append(run_command([sys.executable, *command]))

    for race_no in scope.race_nos:
        results.append(
            run_command(
                [
                    sys.executable,
                    "scripts/scrape_race_cards.py",
                    "--race-date",
                    scope.race_date,
                    "--racecourse",
                    scope.racecourse,
                    "--race-no",
                    str(race_no),
                ]
            )
        )
        results.append(
            run_command(
                [
                    sys.executable,
                    "scripts/scrape_results.py",
                    "--race-date",
                    scope.race_date,
                    "--racecourse",
                    scope.racecourse,
                    "--race-no",
                    str(race_no),
                ]
            )
        )

    for horse_no in scope.horse_nos:
        results.append(
            run_command(
                [
                    sys.executable,
                    "scripts/scrape_horse_history.py",
                    "--horse-no",
                    horse_no,
                ]
            )
        )

    return results


def scrape_once(scopes: list[ScrapeScope], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    results: list[dict[str, object]] = []

    seen_dates = set()
    for scope in scopes:
        if scope.race_date not in seen_dates:
            results.append(
                run_command(
                    [
                        sys.executable,
                        "scripts/scrape_changes.py",
                        "--race-date",
                        scope.race_date,
                    ]
                )
            )
            results.append(
                run_command(
                    [
                        sys.executable,
                        "scripts/scrape_dividends.py",
                        "--race-date",
                        scope.race_date,
                    ]
                )
            )
            seen_dates.add(scope.race_date)

        results.extend(scrape_scope(scope))

    report = {
        "run_id": run_id,
        "scope_count": len(scopes),
        "scopes": [asdict(scope) for scope in scopes],
        "results": results,
    }
    report_path = report_dir / f"hkjc_scrape_run_{run_id}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    results.append(run_command([sys.executable, "scripts/export_scrape_summary.py"]))
    print(f"Wrote {report_path}", flush=True)


def build_scopes(args: argparse.Namespace) -> list[ScrapeScope]:
    racecourses = parse_str_list(args.racecourses or args.racecourse or "HV,ST")
    race_nos = parse_int_list(args.race_nos) if args.race_nos else list(range(1, args.max_race_no + 1))
    horse_nos = parse_str_list(args.horse_nos)

    if args.mode == "local-sample":
        if not args.race_date:
            raise SystemExit("--mode local-sample 需要 --race-date")
        racecourse = args.racecourse or racecourses[0]
        return [ScrapeScope(args.race_date, racecourse.upper(), race_nos, horse_nos)]

    if args.mode == "daily-update":
        target = args.race_date or date.today().isoformat()
        return [ScrapeScope(target, racecourse.upper(), race_nos, horse_nos) for racecourse in racecourses]

    if args.mode == "backfill-history":
        if not args.start_date or not args.end_date:
            raise SystemExit("--mode backfill-history 需要 --start-date 和 --end-date")
        dates = date_range(args.start_date, args.end_date)
        return [
            ScrapeScope(race_date, racecourse.upper(), race_nos, horse_nos)
            for race_date in dates
            for racecourse in racecourses
        ]

    raise SystemExit(f"未知模式：{args.mode}")


def date_range(start_date: str, end_date: str) -> list[str]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise SystemExit("--end-date 不能早于 --start-date")

    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_str_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="定时或一次性更新香港马会公开数据。")
    parser.add_argument(
        "--mode",
        choices=["local-sample", "daily-update", "backfill-history"],
        default="local-sample",
        help="local-sample 小范围验证；daily-update 每日更新；backfill-history 按日期范围回填。",
    )
    parser.add_argument("--race-date", help="单个赛日，例如 2026-05-20。")
    parser.add_argument("--start-date", help="历史回填开始日期，例如 2026-05-01。")
    parser.add_argument("--end-date", help="历史回填结束日期，例如 2026-05-20。")
    parser.add_argument("--racecourse", choices=["ST", "HV", "st", "hv"], help="单个马场：ST 或 HV。")
    parser.add_argument("--racecourses", default="HV,ST", help="马场列表，例如 HV,ST。")
    parser.add_argument("--race-nos", help="场次列表，例如 1,2,3。不填则按 --max-race-no 生成。")
    parser.add_argument("--max-race-no", type=int, default=12, help="未指定 --race-nos 时，默认尝试 1 到该场次。")
    parser.add_argument("--horse-nos", default="", help="马匹编号列表，例如 K099,J087,G394。")
    parser.add_argument("--interval-minutes", type=int, default=60, help="定时更新间隔。")
    parser.add_argument("--once", action="store_true", help="只运行一次，不进入常驻定时模式。")
    parser.add_argument("--report-dir", type=Path, default=Path("data/reports"), help="运行报告目录。")
    args = parser.parse_args()

    scopes = build_scopes(args)
    print(f"Prepared {len(scopes)} scrape scopes.", flush=True)

    if args.once:
        scrape_once(scopes, args.report_dir)
        return

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        scrape_once,
        "interval",
        minutes=args.interval_minutes,
        next_run_time=datetime.now(),
        args=[scopes, args.report_dir],
        id=f"hkjc_{args.mode}",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    print(f"Scheduler started. mode={args.mode} interval={args.interval_minutes} minutes", flush=True)
    scheduler.start()


if __name__ == "__main__":
    main()
