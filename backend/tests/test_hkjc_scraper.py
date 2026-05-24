import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "scripts"))

from hkjc_scraper.client import HkjcClient, normalize_hkjc_date, parse_html_tables


def test_hkjc_urls_are_built_with_expected_params() -> None:
    client = HkjcClient()

    race_card_url = client.race_card_url("2026-05-20", "hv", 1)
    result_url = client.race_result_url("2026-05-20", "HV", 2)
    results_all_url = client.race_results_all_url("2026-05-20")
    entries_url = client.race_entries_url("2026-05-20", "HV")
    changes_url = client.race_changes_url("2026-05-20")
    horse_url = client.horse_url(" e123 ")

    assert "/racecard" in race_card_url
    assert "date=2026-05-20" in race_card_url
    assert "venue=HV" in race_card_url
    assert "raceNo=1" in race_card_url
    assert "LocalResults.aspx" in result_url
    assert "RaceNo=2" in result_url
    assert "ResultsAll.aspx" in results_all_url
    assert "RaceDate=2026%2F05%2F20" in results_all_url
    assert "/entries" in entries_url
    assert "date=2026-05-20" in entries_url
    assert "venue=HV" in entries_url
    assert "View=All" in entries_url
    assert "/changes" in changes_url
    assert "date=2026-05-20" in changes_url
    assert horse_url.endswith("Horse.aspx?HorseNo=E123")


def test_normalize_hkjc_date() -> None:
    assert normalize_hkjc_date("2026-05-20") == "2026/05/20"
    assert normalize_hkjc_date("2026/05/20") == "2026/05/20"


def test_parse_html_tables() -> None:
    parsed = parse_html_tables(
        """
        <html>
          <head><title>Sample</title></head>
          <body>
            <table>
              <tr><th>Horse</th><th>Odds</th></tr>
              <tr><td>1</td><td>3.5</td></tr>
            </table>
          </body>
        </html>
        """
    )

    assert parsed["title"] == "Sample"
    assert parsed["tables"] == [
        {"index": 1, "rows": [["Horse", "Odds"], ["1", "3.5"]]}
    ]
