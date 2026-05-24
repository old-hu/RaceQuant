import argparse
import json
from dataclasses import asdict
from pathlib import Path

from hkjc_scraper.client import HkjcClient


def main() -> None:
    parser = argparse.ArgumentParser(description="局部爬取香港马会完整排位 / 参赛马入口页面。")
    parser.add_argument("--race-date", required=True, help="赛日，例如 2026-05-20。")
    parser.add_argument("--racecourse", required=True, choices=["ST", "HV", "st", "hv"], help="马场：ST 或 HV。")
    parser.add_argument("--output-dir", default="data/raw/hkjc", help="输出目录。")
    args = parser.parse_args()

    client = HkjcClient(output_dir=Path(args.output_dir))
    url = client.race_entries_url(args.race_date, args.racecourse)
    identity = f"{args.race_date}_{args.racecourse}"
    result = client.scrape_url("entries", url, identity)

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
