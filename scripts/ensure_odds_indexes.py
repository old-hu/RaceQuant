from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


INDEX_SQL = [
    """
    CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_race
    ON legacy_horse_odds (race_date, race_no, odds_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_snapshot
    ON legacy_horse_odds (snapshot_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_win_lookup
    ON legacy_horse_odds (race_date, race_no, odds_type, odds_value, snapshot_at DESC, legacy_id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_legacy_horse_odds_final_snapshot
    ON legacy_horse_odds (race_date, race_no, odds_type, snapshot_at DESC)
    """,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="确保旧赔率 SQLite 库具备赛前赔率查询索引。")
    parser.add_argument("--db", type=Path, default=Path("data/processed/legacy_horse_odds.sqlite"))
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    try:
        for sql in INDEX_SQL:
            con.execute(sql)
        con.commit()
        rows = con.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
              AND name NOT LIKE 'sqlite_autoindex_%'
            ORDER BY name
            """
        ).fetchall()
    finally:
        con.close()

    print("Odds indexes ready:")
    for row in rows:
        print(f"- {row[0]}")


if __name__ == "__main__":
    main()
