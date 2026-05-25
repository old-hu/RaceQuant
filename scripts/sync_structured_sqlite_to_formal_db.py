from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.db.models import Horse, Jockey, Race, Result, Runner, Trainer  # noqa: E402
from app.db.session import Base  # noqa: E402


DEFAULT_SQLITE_DB = ROOT / "data" / "processed" / "hkjc_structured.sqlite"


@dataclass
class SyncStats:
    races_seen: int = 0
    races_written: int = 0
    runners_seen: int = 0
    runners_written: int = 0
    results_seen: int = 0
    results_written: int = 0
    skipped_rows: list[str] = field(default_factory=list)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync structured HKJC SQLite data into the formal SQLAlchemy database.")
    parser.add_argument("--sqlite-db", type=Path, default=DEFAULT_SQLITE_DB)
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--dry-run", action="store_true", help="Read and validate source rows without writing the formal database.")
    parser.add_argument("--create-schema", action="store_true", help="Create formal tables before syncing. Prefer Alembic in shared environments.")
    args = parser.parse_args()

    stats = sync_structured_sqlite(
        sqlite_db=args.sqlite_db,
        database_url=args.database_url,
        dry_run=args.dry_run,
        create_schema=args.create_schema,
    )
    print(
        {
            "races_seen": stats.races_seen,
            "races_written": stats.races_written,
            "runners_seen": stats.runners_seen,
            "runners_written": stats.runners_written,
            "results_seen": stats.results_seen,
            "results_written": stats.results_written,
            "skipped_rows": len(stats.skipped_rows),
        }
    )
    if stats.skipped_rows:
        print("sample_skips:")
        for message in stats.skipped_rows[:10]:
            print(f"- {message}")


def sync_structured_sqlite(
    sqlite_db: Path,
    database_url: str,
    dry_run: bool = False,
    create_schema: bool = False,
) -> SyncStats:
    if not sqlite_db.exists():
        raise FileNotFoundError(f"Structured SQLite DB not found: {sqlite_db}")

    con = sqlite3.connect(sqlite_db)
    con.row_factory = sqlite3.Row
    stats = SyncStats()
    try:
        if dry_run:
            count_source_rows(con, stats)
            return stats

        engine = create_engine(database_url, pool_pre_ping=True)
        if create_schema:
            Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine, autoflush=False)
        with SessionLocal() as session:
            sync_races(con, session, stats)
            sync_runners(con, session, stats)
            sync_results(con, session, stats)
            session.commit()
        return stats
    finally:
        con.close()


def count_source_rows(con: sqlite3.Connection, stats: SyncStats) -> None:
    stats.races_seen = table_count(con, "race_metadata")
    stats.runners_seen = table_count(con, "race_entries")
    stats.results_seen = table_count(con, "race_results")


def sync_races(con: sqlite3.Connection, session: Session, stats: SyncStats) -> None:
    for row in con.execute("SELECT * FROM race_metadata ORDER BY race_date, racecourse, race_no"):
        stats.races_seen += 1
        race = get_or_create_race(session, row, stats)
        if race is not None:
            stats.races_written += 1


def sync_runners(con: sqlite3.Connection, session: Session, stats: SyncStats) -> None:
    query = """
        SELECT * FROM race_entries
        ORDER BY race_date, racecourse, race_no, CAST(horse_no AS INTEGER), standby
    """
    for row in con.execute(query):
        stats.runners_seen += 1
        race = get_or_create_race(session, row, stats)
        horse_no = parse_int(row["horse_no"])
        if race is None or horse_no is None:
            stats.skipped_rows.append(f"runner missing race or horse_no: {row_key(row)}")
            continue
        upsert_runner(session, race, row, horse_no)
        stats.runners_written += 1


def sync_results(con: sqlite3.Connection, session: Session, stats: SyncStats) -> None:
    query = """
        SELECT * FROM race_results
        ORDER BY race_date, racecourse, race_no, CAST(horse_no AS INTEGER)
    """
    for row in con.execute(query):
        stats.results_seen += 1
        race = get_or_create_race(session, row, stats)
        horse_no = parse_int(row["horse_no"])
        if race is None or horse_no is None:
            stats.skipped_rows.append(f"result missing race or horse_no: {row_key(row)}")
            continue
        runner = upsert_runner(session, race, row, horse_no)
        upsert_result(session, runner, row)
        stats.results_written += 1


def get_or_create_race(session: Session, row: sqlite3.Row, stats: SyncStats) -> Race | None:
    race_date = parse_date(row["race_date"])
    racecourse = normalized_text(row["racecourse"])
    race_no = parse_int(row["race_no"])
    if race_date is None or racecourse is None or race_no is None:
        stats.skipped_rows.append(f"race missing key: {row_key(row)}")
        return None

    race = session.scalar(
        select(Race).where(
            Race.race_date == race_date,
            Race.racecourse == racecourse,
            Race.race_no == race_no,
        )
    )
    if race is None:
        race = Race(race_date=race_date, racecourse=racecourse, race_no=race_no)
        session.add(race)
        session.flush()

    race.distance_m = parse_int(row_get(row, "distance_m"))
    race.surface = normalized_text(row_get(row, "surface"))
    race.going = normalized_text(row_get(row, "going"))
    race.race_class = normalized_text(row_get(row, "race_class"))
    race.name = normalized_text(row_get(row, "race_name"))
    return race


def upsert_runner(session: Session, race: Race, row: sqlite3.Row, horse_no: int) -> Runner:
    runner = session.scalar(select(Runner).where(Runner.race_id == race.id, Runner.horse_no == horse_no))
    if runner is None:
        runner = Runner(race_id=race.id, horse_no=horse_no)
        session.add(runner)
        session.flush()

    horse_code = normalized_text(row_get(row, "horse_code"))
    if horse_code:
        runner.horse = get_or_create_horse(session, horse_code, normalized_text(row_get(row, "horse_name")))
    runner.jockey = get_or_create_person(session, Jockey, normalized_text(row_get(row, "jockey")))
    runner.trainer = get_or_create_person(session, Trainer, normalized_text(row_get(row, "trainer")))
    runner.draw = parse_int(row_get(row, "draw"))
    runner.carried_weight_lbs = parse_int(row_get(row, "actual_weight"))
    runner.declared_rating = parse_int(row_get(row, "rating"))
    runner.gear = normalized_text(row_get(row, "gear"))
    runner.status = "standby" if parse_int(row_get(row, "standby")) == 1 else "declared"
    return runner


def upsert_result(session: Session, runner: Runner, row: sqlite3.Row) -> Result:
    result = session.scalar(select(Result).where(Result.runner_id == runner.id))
    if result is None:
        result = Result(race_id=runner.race_id, runner_id=runner.id)
        session.add(result)
    result.finishing_position = parse_int(row_get(row, "place"))
    result.beaten_margin = normalized_text(row_get(row, "lbw"))
    result.win_dividend = parse_decimal(row_get(row, "win_odds"))
    return result


def get_or_create_horse(session: Session, horse_code: str, horse_name: str | None) -> Horse:
    horse = session.scalar(select(Horse).where(Horse.hkjc_id == horse_code))
    if horse is None:
        horse = Horse(hkjc_id=horse_code)
        session.add(horse)
    horse.name_en = horse_name
    return horse


def get_or_create_person(session: Session, model: type[Jockey] | type[Trainer], name: str | None) -> Any | None:
    if not name:
        return None
    person = session.scalar(select(model).where(model.name_en == name))
    if person is None:
        person = model(name_en=name)
        session.add(person)
    return person


def table_count(con: sqlite3.Connection, table_name: str) -> int:
    exists = con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)).fetchone()
    if exists is None:
        return 0
    return int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def row_get(row: sqlite3.Row, key: str) -> Any:
    return row[key] if key in row.keys() else None


def row_key(row: sqlite3.Row) -> str:
    return f"{row_get(row, 'race_date')}/{row_get(row, 'racecourse')}/R{row_get(row, 'race_no')}/H{row_get(row, 'horse_no')}"


def normalized_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return None if text in {"", "-", "--"} else text


def parse_date(value: Any) -> date | None:
    text = normalized_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    text = normalized_text(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_decimal(value: Any) -> Decimal | None:
    text = normalized_text(value)
    if text is None:
        return None
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


if __name__ == "__main__":
    main()
