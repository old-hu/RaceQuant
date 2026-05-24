from __future__ import annotations

import argparse
from pathlib import Path

from hkjc_structured_store import connect


def main() -> None:
    parser = argparse.ArgumentParser(description="确保结构化 SQLite 库具备特征生成所需索引。")
    parser.add_argument("--db", type=Path, default=Path("data/processed/hkjc_structured.sqlite"))
    args = parser.parse_args()

    con = connect(args.db)
    indexes = con.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'index'
          AND name NOT LIKE 'sqlite_autoindex_%'
        ORDER BY name
        """
    ).fetchall()
    con.close()
    print("Structured indexes ready:")
    for row in indexes:
        print(f"- {row['name']}")


if __name__ == "__main__":
    main()
