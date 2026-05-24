import argparse
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.quant.backtesting.engine import table_exists
from app.services import odds_repository


def main() -> None:
    parser = argparse.ArgumentParser(description="导出历史赔率变化序列给前端展示。")
    parser.add_argument("--race-date")
    parser.add_argument("--race-no", type=int)
    parser.add_argument("--odds-type", default="win", choices=["win", "fct", "qin", "qpl"])
    parser.add_argument("--limit-values", type=int, default=12)
    parser.add_argument("--output", type=Path, default=Path("frontend/public/data/odds_changes.json"))
    args = parser.parse_args()

    race_date = args.race_date
    race_no = args.race_no
    if race_date is None or race_no is None:
        race_date, race_no = latest_race()
    payload = {
        "raceDate": race_date,
        "raceNo": race_no,
        "oddsType": args.odds_type,
        "series": odds_repository.list_changes(
            race_date=race_date,
            race_no=race_no,
            odds_type=args.odds_type,
            limit_values=args.limit_values,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['series'])} odds series to {args.output}")


def latest_race() -> tuple[str, int]:
    with odds_repository.get_connection() as con:
        if not table_exists(con, "legacy_horse_odds"):
            raise RuntimeError("legacy_horse_odds table does not exist.")
        row = con.execute(
            """
            SELECT race_date, race_no
            FROM legacy_horse_odds
            WHERE race_date IS NOT NULL AND race_no IS NOT NULL
            GROUP BY race_date, race_no
            ORDER BY race_date DESC, race_no ASC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            raise RuntimeError("No odds rows available.")
        return row["race_date"], int(row["race_no"])


if __name__ == "__main__":
    main()

