import argparse
import json
from dataclasses import asdict
from pathlib import Path

from hkjc_scraper.client import HkjcClient


def main() -> None:
    parser = argparse.ArgumentParser(description="局部爬取香港马会历史赛果页面。")
    parser.add_argument("--race-date", required=True, help="赛日，例如 2026-05-20。")
    parser.add_argument("--racecourse", required=True, choices=["ST", "HV", "st", "hv"], help="马场：ST 或 HV。")
    parser.add_argument("--race-no", type=int, help="场次。不填则抓取该赛日页面默认场次。")
    parser.add_argument("--output-dir", default="data/raw/hkjc", help="输出目录。")
    args = parser.parse_args()

    client = HkjcClient(output_dir=Path(args.output_dir))
    url = client.race_result_url(args.race_date, args.racecourse, args.race_no)
    identity = f"{args.race_date}_{args.racecourse}_R{args.race_no or 'default'}"
    result = client.scrape_url("results", url, identity)

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

