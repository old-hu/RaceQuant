import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "race_date",
    "racecourse",
    "race_no",
    "horse_no",
    "bet_type",
    "odds",
    "snapshot_at",
}


@dataclass
class MigrationReport:
    input_path: str
    total_rows: int = 0
    valid_rows: int = 0
    error_rows: int = 0
    duplicate_rows: int = 0
    race_count: int = 0
    snapshot_count: int = 0
    sources: list[str] | None = None
    errors: list[dict[str, Any]] | None = None


def parse_decimal(value: str) -> Decimal:
    try:
        odds = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("odds must be numeric") from exc

    if odds <= Decimal("1"):
        raise ValueError("odds must be greater than 1")

    return odds


def parse_snapshot_at(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("snapshot_at must be ISO-like datetime") from exc


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if not row.get(field)]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")

    odds = parse_decimal(row["odds"].strip())
    snapshot_at = parse_snapshot_at(row["snapshot_at"])

    return {
        "race_date": row["race_date"].strip(),
        "racecourse": row["racecourse"].strip(),
        "race_no": int(row["race_no"]),
        "horse_no": int(row["horse_no"]),
        "horse_name": row.get("horse_name", "").strip(),
        "bet_type": row["bet_type"].strip().lower(),
        "odds": str(odds),
        "implied_probability": str((Decimal("1") / odds).quantize(Decimal("0.000001"))),
        "snapshot_at": snapshot_at.isoformat(),
        "source": row.get("source", "unknown").strip() or "unknown",
        "pool_size": row.get("pool_size", "").strip(),
    }


def row_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["race_date"],
        row["racecourse"],
        row["race_no"],
        row["horse_no"],
        row["bet_type"],
        row["snapshot_at"],
        row["source"],
    )


def migrate(input_path: Path) -> tuple[list[dict[str, Any]], MigrationReport]:
    report = MigrationReport(input_path=str(input_path), errors=[], sources=[])
    normalized_rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    races: set[tuple[str, str, int]] = set()
    sources: set[str] = set()

    with input_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row_number, row in enumerate(reader, start=2):
            report.total_rows += 1
            try:
                normalized = normalize_row(row)
            except Exception as exc:
                report.error_rows += 1
                report.errors.append({"row": row_number, "error": str(exc)})
                continue

            key = row_key(normalized)
            if key in seen:
                report.duplicate_rows += 1
                continue

            seen.add(key)
            races.add((normalized["race_date"], normalized["racecourse"], normalized["race_no"]))
            sources.add(normalized["source"])
            normalized_rows.append(normalized)

    report.valid_rows = len(normalized_rows)
    report.race_count = len(races)
    report.snapshot_count = len(normalized_rows)
    report.sources = sorted(sources)

    return normalized_rows, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate historical odds movement data.")
    parser.add_argument("--input", required=True, type=Path, help="Source CSV path.")
    parser.add_argument("--normalized-output", type=Path, help="Optional normalized CSV output path.")
    parser.add_argument("--report", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()

    rows, report = migrate(args.input)

    if args.normalized_output:
        args.normalized_output.parent.mkdir(parents=True, exist_ok=True)
        with args.normalized_output.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

