import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "scripts"))

from schedule_scrapers import build_scopes, date_range


def test_date_range_is_inclusive() -> None:
    assert date_range("2026-05-20", "2026-05-22") == [
        "2026-05-20",
        "2026-05-21",
        "2026-05-22",
    ]


def test_build_backfill_scopes_crosses_dates_and_racecourses() -> None:
    args = argparse.Namespace(
        mode="backfill-history",
        race_date=None,
        start_date="2026-05-20",
        end_date="2026-05-21",
        racecourse=None,
        racecourses="HV,ST",
        race_nos="1,2",
        max_race_no=12,
        horse_nos="K099",
    )

    scopes = build_scopes(args)

    assert [scope.race_date for scope in scopes] == [
        "2026-05-20",
        "2026-05-20",
        "2026-05-21",
        "2026-05-21",
    ]
    assert [scope.racecourse for scope in scopes] == ["HV", "ST", "HV", "ST"]
    assert scopes[0].race_nos == [1, 2]
    assert scopes[0].horse_nos == ["K099"]
