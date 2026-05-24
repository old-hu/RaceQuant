import argparse
import json
from dataclasses import asdict
from pathlib import Path

from hkjc_scraper.client import HkjcClient


def main() -> None:
    parser = argparse.ArgumentParser(description="局部爬取香港马会赛事临场变更页面。")
    parser.add_argument("--race-date", required=True, help="赛日，例如 2026-05-20。")
    parser.add_argument("--output-dir", default="data/raw/hkjc", help="输出目录。")
    args = parser.parse_args()

    client = HkjcClient(output_dir=Path(args.output_dir))
    url = client.race_changes_url(args.race_date)
    result = client.scrape_url("changes", url, args.race_date)

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
