from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.hkjc_structured_store import connect, missing_horse_history_codes, next_pending_job, race_day_has_core_data
from scripts.run_historical_scrape_worker import run_horse_history_command, run_meeting_commands, run_next_job, run_race_commands


def test_worker_scrape_commands_pass_raw_output_dir(monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_run_command(command: list[str]) -> dict[str, object]:
        commands.append(command)
        return {"returncode": 0}

    monkeypatch.setattr("scripts.run_historical_scrape_worker.run_command", fake_run_command)

    run_meeting_commands("2026-05-20", "HV", Path("data/raw/custom"))
    run_race_commands("2026-05-20", "HV", 1, Path("data/raw/custom"))

    assert commands
    assert all("--output-dir" in command for command in commands)
    assert all("data\\raw\\custom" in " ".join(command) or "data/raw/custom" in " ".join(command) for command in commands)


def test_worker_horse_history_command_passes_raw_output_dir(monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_run_command(command: list[str]) -> dict[str, object]:
        commands.append(command)
        return {"returncode": 0}

    monkeypatch.setattr("scripts.run_historical_scrape_worker.run_command", fake_run_command)

    run_horse_history_command("K099", Path("data/raw/custom"))

    assert commands == [
        [
            sys.executable,
            "scripts/scrape_horse_history.py",
            "--horse-no",
            "K099",
            "--output-dir",
            "data\\raw\\custom" if "\\" in str(Path("data/raw/custom")) else "data/raw/custom",
        ]
    ]


def test_missing_horse_history_codes_discovers_entries_and_results(tmp_path) -> None:
    db_path = tmp_path / "structured.sqlite"
    raw_dir = tmp_path / "raw"
    con = connect(db_path)
    con.execute(
        """
        INSERT INTO race_entries (
            race_date, racecourse, race_no, horse_no, horse_code, standby, source_path, updated_at
        )
        VALUES ('2026-05-20', 'HV', 1, '1', 'K099', 0, 'test', 'now')
        """
    )
    con.execute(
        """
        INSERT INTO race_results (
            race_date, racecourse, race_no, place, horse_no, horse_code, source_path, updated_at
        )
        VALUES ('2026-05-20', 'HV', 1, '1', '2', 'J123', 'test', 'now')
        """
    )
    con.commit()
    con.close()

    (raw_dir / "horse_history" / "K099").mkdir(parents=True)
    (raw_dir / "horse_history" / "K099" / "latest.json").write_text("{}", encoding="utf-8")

    assert missing_horse_history_codes(db_path=db_path, raw_dir=raw_dir) == ["J123"]
    assert missing_horse_history_codes(db_path=db_path, raw_dir=raw_dir, include_existing=True) == ["J123", "K099"]


def test_next_pending_job_defers_failed_jobs(tmp_path) -> None:
    db_path = tmp_path / "structured.sqlite"
    con = connect(db_path)
    con.execute("INSERT INTO scrape_jobs (race_date, racecourse, status) VALUES ('2026-05-20', 'HV', 'failed')")
    con.execute("INSERT INTO scrape_jobs (race_date, racecourse, status) VALUES ('2026-05-18', 'ST', 'pending')")
    con.commit()
    con.close()

    job = next_pending_job(db_path)

    assert job is not None
    assert job["race_date"] == "2026-05-18"
    assert job["racecourse"] == "ST"


def test_worker_parses_available_raw_and_records_failed_job(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "structured.sqlite"
    raw_dir = tmp_path / "raw"
    report_dir = tmp_path / "reports"
    con = connect(db_path)
    con.execute("INSERT INTO scrape_jobs (race_date, racecourse) VALUES ('2026-05-20', 'HV')")
    con.commit()
    con.close()

    def fake_run_meeting_commands(race_date: str, racecourse: str, raw_path: Path) -> list[dict[str, object]]:
        return [{"returncode": 1, "command": ["meeting"], "stderr": "temporary TLS failure"}]

    def fake_run_race_commands(race_date: str, racecourse: str, race_no: int, raw_path: Path) -> list[dict[str, object]]:
        return [{"returncode": 0, "command": ["race", str(race_no)], "stdout": "ok"}]

    def fake_parse_job_outputs(*args, **kwargs) -> dict[str, int]:
        return {"race_results": 3, "dividends": 2, "race_entries": 4}

    monkeypatch.setattr("scripts.run_historical_scrape_worker.run_meeting_commands", fake_run_meeting_commands)
    monkeypatch.setattr("scripts.run_historical_scrape_worker.run_race_commands", fake_run_race_commands)
    monkeypatch.setattr("scripts.run_historical_scrape_worker.parse_job_outputs", fake_parse_job_outputs)
    monkeypatch.setattr("scripts.run_historical_scrape_worker.parse_change_outputs", lambda **kwargs: {"race_change_events": 0})
    monkeypatch.setattr("scripts.run_historical_scrape_worker.run_command", lambda command: {"returncode": 0})

    run_next_job(1, report_dir, db_path=db_path, raw_dir=raw_dir, max_horse_histories=0)

    con = connect(db_path)
    row = con.execute("SELECT status, last_error FROM scrape_jobs WHERE race_date = '2026-05-20'").fetchone()
    con.close()
    assert row["status"] == "failed"
    assert "temporary TLS failure" in row["last_error"]


def test_worker_marks_done_with_warnings_when_core_data_exists(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "structured.sqlite"
    raw_dir = tmp_path / "raw"
    report_dir = tmp_path / "reports"
    con = connect(db_path)
    con.execute("INSERT INTO scrape_jobs (race_date, racecourse) VALUES ('2026-05-20', 'HV')")
    con.commit()
    con.close()

    def fake_parse_job_outputs(*args, **kwargs) -> dict[str, int]:
        con = connect(db_path)
        con.execute(
            "INSERT INTO race_metadata (race_date, racecourse, race_no, source_path, updated_at) VALUES ('2026-05-20', 'HV', 1, 'test', 'now')"
        )
        con.execute(
            "INSERT INTO race_entries (race_date, racecourse, race_no, horse_no, standby, source_path, updated_at) VALUES ('2026-05-20', 'HV', 1, '1', 0, 'test', 'now')"
        )
        con.execute(
            "INSERT INTO race_results (race_date, racecourse, race_no, place, horse_no, source_path, updated_at) VALUES ('2026-05-20', 'HV', 1, '1', '1', 'test', 'now')"
        )
        con.execute(
            "INSERT INTO dividends (race_date, racecourse, race_no, pool, winning_combination, dividend, source_path, updated_at) VALUES ('2026-05-20', 'HV', 1, 'WIN', '1', '10.0', 'test', 'now')"
        )
        con.commit()
        con.close()
        return {"race_results": 1, "dividends": 1, "race_entries": 1}

    monkeypatch.setattr(
        "scripts.run_historical_scrape_worker.run_meeting_commands",
        lambda race_date, racecourse, raw_path: [{"returncode": 1, "command": ["meeting"], "stderr": "temporary TLS failure"}],
    )
    monkeypatch.setattr("scripts.run_historical_scrape_worker.run_race_commands", lambda *args: [])
    monkeypatch.setattr("scripts.run_historical_scrape_worker.parse_job_outputs", fake_parse_job_outputs)
    monkeypatch.setattr("scripts.run_historical_scrape_worker.parse_change_outputs", lambda **kwargs: {"race_change_events": 0})
    monkeypatch.setattr("scripts.run_historical_scrape_worker.run_command", lambda command: {"returncode": 0})

    run_next_job(1, report_dir, db_path=db_path, raw_dir=raw_dir, max_horse_histories=0)

    con = connect(db_path)
    row = con.execute("SELECT status, last_error FROM scrape_jobs WHERE race_date = '2026-05-20'").fetchone()
    con.close()
    assert row["status"] == "done_with_warnings"
    assert "temporary TLS failure" in row["last_error"]
    assert race_day_has_core_data("2026-05-20", "HV", db_path=db_path)
