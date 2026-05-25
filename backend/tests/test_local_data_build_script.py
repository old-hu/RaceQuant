from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.build_local_data import choose_source, has_raw_cache


def test_choose_source_prefers_raw_when_cache_exists(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw" / "results" / "2026-05-20_HV_R1"
    raw_dir.mkdir(parents=True)
    (raw_dir / "latest.json").write_text("{}", encoding="utf-8")

    assert has_raw_cache(tmp_path / "raw")
    assert choose_source("auto", tmp_path / "raw", tmp_path / "exports") == "raw"


def test_choose_source_falls_back_to_json_cache_without_raw(tmp_path: Path) -> None:
    assert not has_raw_cache(tmp_path / "raw")
    assert choose_source("auto", tmp_path / "raw", tmp_path / "exports") == "json-cache"
    assert choose_source("raw", tmp_path / "raw", tmp_path / "exports") == "raw"
    assert choose_source("json-cache", tmp_path / "raw", tmp_path / "exports") == "json-cache"
