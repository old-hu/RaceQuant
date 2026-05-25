from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from hkjc_scraper.client import HkjcClient
from hkjc_structured_store import (
    STRUCTURED_DB,
    missing_horse_history_codes,
    parse_horse_history_outputs,
    set_raw_dir,
)


def scrape_horse_histories(
    db_path: Path = STRUCTURED_DB,
    raw_dir: Path = Path("data/raw/hkjc"),
    limit: int | None = None,
    include_existing: bool = False,
    sleep_seconds: float = 0.2,
    flush_every: int = 50,
) -> dict[str, object]:
    set_raw_dir(raw_dir)
    codes = missing_horse_history_codes(
        db_path=db_path,
        raw_dir=raw_dir,
        limit=limit,
        include_existing=include_existing,
    )
    client = HkjcClient(output_dir=raw_dir)
    results: list[dict[str, object]] = []
    failed: list[dict[str, str]] = []

    for index, horse_code in enumerate(codes, start=1):
        try:
            result = client.scrape_url("horse_history", client.horse_url(horse_code), horse_code)
            results.append(asdict(result))
            print(f"[{index}/{len(codes)}] scraped horse history {horse_code}", flush=True)
        except Exception as exc:
            failed.append({"horseCode": horse_code, "error": str(exc)})
            print(f"[{index}/{len(codes)}] failed horse history {horse_code}: {exc}", flush=True)
        if flush_every > 0 and index % flush_every == 0:
            structured = flush_outputs(db_path, raw_dir)
            print(f"Flushed horse history outputs after {index} horses: {structured}", flush=True)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    structured = flush_outputs(db_path, raw_dir)
    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "requested": len(codes),
        "succeeded": len(results),
        "failed": len(failed),
        "failures": failed,
        "structured": structured,
    }


def flush_outputs(db_path: Path, raw_dir: Path) -> dict[str, object]:
    structured = parse_horse_history_outputs(db_path=db_path)
    export_results = [
        run_command([sys.executable, "scripts/export_scrape_summary.py", "--raw-dir", str(raw_dir)]),
        run_command([sys.executable, "scripts/export_structured_data.py", "--db", str(db_path)]),
    ]
    return {"parsed": structured, "exports": export_results}


def run_command(command: list[str]) -> dict[str, object]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape official HKJC horse history pages for every horse found in structured entries/results.")
    parser.add_argument("--db", type=Path, default=STRUCTURED_DB)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/hkjc"))
    parser.add_argument("--limit", type=int, default=0, help="Maximum horse histories to scrape. 0 means all missing histories.")
    parser.add_argument("--include-existing", action="store_true", help="Re-scrape horses that already have a raw latest.json.")
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--flush-every", type=int, default=50, help="Parse and export after this many scraped horses. 0 disables intermediate flushes.")
    parser.add_argument("--report", type=Path, default=Path("data/reports/horse_history_scrape_latest.json"))
    args = parser.parse_args()

    summary = scrape_horse_histories(
        db_path=args.db,
        raw_dir=args.raw_dir,
        limit=args.limit if args.limit > 0 else None,
        include_existing=args.include_existing,
        sleep_seconds=args.sleep_seconds,
        flush_every=args.flush_every,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
