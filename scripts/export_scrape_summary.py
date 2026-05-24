from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


CATEGORY_BY_KIND = {
    "race_meetings": "赛程 / 赛日",
    "entries": "完整排位",
    "race_cards": "排位 / 参赛马",
    "results": "历史赛果",
    "dividends": "派彩结果",
    "changes": "临场变更",
    "horse_history": "马匹历史",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="导出爬虫 latest.json 摘要，供前端数据页展示。")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/hkjc"), help="爬虫原始数据目录。")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("frontend/public/data/scrape-summary.json"),
        help="前端可读取的 JSON 输出路径。",
    )
    args = parser.parse_args()

    source_rows = []
    race_day_counts: dict[str, int] = defaultdict(int)

    for latest_path in sorted(args.raw_dir.glob("*/*/latest.json")):
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
        kind = payload.get("kind", latest_path.parents[1].name)
        identity = latest_path.parent.name
        category = CATEGORY_BY_KIND.get(kind, kind)
        race_date = extract_date(identity)
        record_count = payload.get("table_count") or payload.get("text_block_count") or 0

        if race_date:
            race_day_counts[race_date] += int(record_count)

        source_rows.append(
            {
                "id": f"{kind}-{identity}",
                "category": category,
                "source": identity.replace("_", " "),
                "title": payload.get("title") or category,
                "recordCount": record_count,
                "updatedAt": format_timestamp(payload.get("fetched_at")),
            }
        )

    race_days = [
        {"date": race_date, "rows": rows}
        for race_date, rows in sorted(race_day_counts.items(), reverse=True)
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
                "raceDays": race_days,
                "sourceRows": source_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")


def extract_date(value: str) -> str | None:
    parts = value.split("_")
    if parts and len(parts[0]) == 10 and parts[0][4] == "-" and parts[0][7] == "-":
        return parts[0]
    return None


def format_timestamp(value: Any) -> str:
    if not value:
        return "-"
    text = str(value)
    try:
        return datetime.fromisoformat(text).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text[:16]


if __name__ == "__main__":
    main()
