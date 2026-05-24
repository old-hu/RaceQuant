import argparse
import json
from dataclasses import asdict
from pathlib import Path

from hkjc_scraper.client import HkjcClient


def main() -> None:
    parser = argparse.ArgumentParser(description="局部爬取香港马会马匹历史表现页面。")
    parser.add_argument("--horse-no", required=True, help="香港马会马匹编号，例如 E123。")
    parser.add_argument("--output-dir", default="data/raw/hkjc", help="输出目录。")
    args = parser.parse_args()

    client = HkjcClient(output_dir=Path(args.output_dir))
    url = client.horse_url(args.horse_no)
    result = client.scrape_url("horse_history", url, args.horse_no)

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

