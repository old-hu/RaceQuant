import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from scripts.migrate_odds_history import migrate


def test_migrate_odds_history_csv(tmp_path: Path) -> None:
    input_path = tmp_path / "odds.csv"
    input_path.write_text(
        "\n".join(
            [
                "race_date,racecourse,race_no,horse_no,horse_name,bet_type,odds,snapshot_at,source,pool_size",
                "2026-05-01,Sha Tin,1,3,Test Horse,win,5.0,2026-05-01T12:00:00+08:00,hkjc,100000",
                "2026-05-01,Sha Tin,1,3,Test Horse,win,5.0,2026-05-01T12:00:00+08:00,hkjc,100000",
                "2026-05-01,Sha Tin,1,4,Bad Horse,win,1.0,2026-05-01T12:01:00+08:00,hkjc,100000",
            ]
        ),
        encoding="utf-8",
    )

    rows, report = migrate(input_path)

    assert len(rows) == 1
    assert report.total_rows == 3
    assert report.valid_rows == 1
    assert report.duplicate_rows == 1
    assert report.error_rows == 1
    assert rows[0]["implied_probability"] == "0.200000"

