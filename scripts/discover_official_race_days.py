from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from hkjc_scraper.client import HkjcClient, parse_html_tables  # noqa: E402
from hkjc_structured_store import connect  # noqa: E402


VENUE_LABELS = {
    "Happy Valley": "HV",
    "Sha Tin": "ST",
}


@dataclass(frozen=True)
class DiscoveryResult:
    scanned_dates: int
    race_days: int
    meeting_count: int
    inserted_jobs: int
    report_path: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover HKJC official historical race days from ResultsAll.aspx.")
    parser.add_argument("--start-date", default="1996-01-01")
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/reports"))
    parser.add_argument("--sleep-seconds", type=float, default=0.15)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--limit", type=int, help="Limit scanned dates for smoke tests.")
    parser.add_argument("--skip-scanned", action="store_true", help="Skip dates already recorded in official_race_day_scans.")
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--prune-undiscovered-pending", action="store_true")
    args = parser.parse_args()

    result = discover_and_seed(
        start_date=date.fromisoformat(args.start_date),
        end_date=date.fromisoformat(args.end_date),
        db_path=args.db,
        output_dir=args.output_dir,
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
        limit=args.limit,
        skip_scanned=args.skip_scanned,
        progress_every=args.progress_every,
        prune_undiscovered_pending=args.prune_undiscovered_pending,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


def discover_and_seed(
    start_date: date,
    end_date: date,
    db_path: Path,
    output_dir: Path,
    sleep_seconds: float,
    timeout_seconds: int,
    limit: int | None = None,
    skip_scanned: bool = False,
    progress_every: int = 100,
    prune_undiscovered_pending: bool = False,
) -> DiscoveryResult:
    if end_date < start_date:
        raise ValueError("end_date must be greater than or equal to start_date.")

    con = connect(db_path)
    init_discovery_schema(con)
    client = HkjcClient(timeout_seconds=timeout_seconds)
    rows: list[dict[str, Any]] = []
    scanned_dates = 0
    inserted_jobs = 0

    for race_date in iter_dates(start_date, end_date):
        if limit is not None and scanned_dates >= limit:
            break
        text_date = race_date.isoformat()
        if skip_scanned and already_scanned(con, text_date):
            continue
        scanned_dates += 1
        url = client.race_results_all_url(text_date)
        try:
            parsed = parse_html_tables(client.fetch(url))
            venues = venues_from_results_all(parsed)
            error = None
        except Exception as exc:
            parsed = {"title": None, "tables": [], "text_blocks": []}
            venues = []
            error = str(exc)

        save_scan(con, text_date, url, parsed, venues, error)
        for venue in venues:
            inserted_jobs += insert_scrape_job(con, text_date, venue)
        rows.append(
            {
                "raceDate": text_date,
                "venues": venues,
                "tableCount": len(parsed.get("tables", [])),
                "error": error,
            }
        )
        con.commit()
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
        if progress_every > 0 and scanned_dates % progress_every == 0:
            print(
                f"scanned={scanned_dates} current={text_date} race_days={sum(1 for row in rows if row['venues'])} jobs={inserted_jobs}",
                flush=True,
            )

    if prune_undiscovered_pending and limit is None:
        prune_pending_jobs_not_discovered(con, start_date.isoformat(), end_date.isoformat())
        con.commit()

    report = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "scannedDates": scanned_dates,
        "raceDays": sum(1 for row in rows if row["venues"]),
        "meetingCount": sum(len(row["venues"]) for row in rows),
        "insertedJobs": inserted_jobs,
        "rows": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"official_race_day_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    con.close()
    return DiscoveryResult(
        scanned_dates=scanned_dates,
        race_days=report["raceDays"],
        meeting_count=report["meetingCount"],
        inserted_jobs=inserted_jobs,
        report_path=str(report_path),
    )


def init_discovery_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS official_race_day_scans (
            race_date TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            table_count INTEGER NOT NULL,
            venues_json TEXT NOT NULL,
            error TEXT,
            scanned_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS official_race_days (
            race_date TEXT NOT NULL,
            racecourse TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'hkjc_results_all',
            discovered_at TEXT NOT NULL,
            PRIMARY KEY (race_date, racecourse)
        );
        """
    )
    con.commit()


def venues_from_results_all(parsed: dict[str, Any]) -> list[str]:
    venues: list[str] = []
    for table in parsed.get("tables", []):
        rows = table.get("rows", [])
        if not rows or not rows[0]:
            continue
        label = str(rows[0][0]).strip().rstrip(":")
        venue = VENUE_LABELS.get(label)
        if venue and venue not in venues:
            venues.append(venue)
    return venues


def save_scan(
    con: sqlite3.Connection,
    race_date: str,
    url: str,
    parsed: dict[str, Any],
    venues: list[str],
    error: str | None,
) -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    con.execute(
        """
        INSERT OR REPLACE INTO official_race_day_scans (
            race_date, url, table_count, venues_json, error, scanned_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (race_date, url, len(parsed.get("tables", [])), json.dumps(venues), error, now),
    )
    for venue in venues:
        con.execute(
            """
            INSERT OR REPLACE INTO official_race_days (
                race_date, racecourse, source, discovered_at
            )
            VALUES (?, ?, 'hkjc_results_all', ?)
            """,
            (race_date, venue, now),
        )


def insert_scrape_job(con: sqlite3.Connection, race_date: str, racecourse: str) -> int:
    cur = con.execute(
        """
        INSERT OR IGNORE INTO scrape_jobs (race_date, racecourse)
        VALUES (?, ?)
        """,
        (race_date, racecourse),
    )
    return int(cur.rowcount)


def already_scanned(con: sqlite3.Connection, race_date: str) -> bool:
    row = con.execute(
        """
        SELECT 1
        FROM official_race_day_scans
        WHERE race_date = ?
          AND error IS NULL
        """,
        (race_date,),
    ).fetchone()
    return row is not None


def prune_pending_jobs_not_discovered(con: sqlite3.Connection, start_date: str, end_date: str) -> None:
    con.execute(
        """
        UPDATE scrape_jobs
        SET status = 'skipped_no_official_result',
            finished_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            last_error = 'No matching HKJC ResultsAll race day discovered.'
        WHERE status IN ('pending', 'failed')
          AND race_date BETWEEN ? AND ?
          AND NOT EXISTS (
              SELECT 1
              FROM official_race_days d
              WHERE d.race_date = scrape_jobs.race_date
                AND d.racecourse = scrape_jobs.racecourse
          )
        """,
        (start_date, end_date),
    )


def iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


if __name__ == "__main__":
    main()
