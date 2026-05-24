from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from hkjc_structured_store import connect, seed_jobs_from_legacy_odds


def seed_jobs_from_date_range(
    start_date: date,
    end_date: date,
    racecourses: tuple[str, ...],
    db: Path,
) -> int:
    con = connect(db)
    inserted = 0
    current = start_date
    while current <= end_date:
        race_date = current.isoformat()
        for racecourse in racecourses:
            cur = con.execute(
                """
                INSERT OR IGNORE INTO scrape_jobs (race_date, racecourse)
                VALUES (?, ?)
                """,
                (race_date, racecourse),
            )
            inserted += cur.rowcount
        current += timedelta(days=1)
    con.commit()
    con.close()
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="生成历史全量爬取队列。")
    parser.add_argument("--legacy-db", type=Path, default=Path("data/processed/legacy_horse_odds.sqlite"))
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    parser.add_argument("--racecourses", default="HV,ST", help="马场列表，例如 HV,ST。")
    parser.add_argument("--start-date", help="按日期范围补队列，例如 2025-09-01。")
    parser.add_argument("--end-date", help="按日期范围补队列，例如 2026-05-24。")
    args = parser.parse_args()

    racecourses = tuple(item.strip().upper() for item in args.racecourses.split(",") if item.strip())
    if args.start_date and args.end_date:
        inserted = seed_jobs_from_date_range(
            date.fromisoformat(args.start_date),
            date.fromisoformat(args.end_date),
            racecourses,
            args.db,
        )
    else:
        inserted = seed_jobs_from_legacy_odds(args.legacy_db, args.db, racecourses)
    print(f"Inserted {inserted} scrape jobs.")


if __name__ == "__main__":
    main()
