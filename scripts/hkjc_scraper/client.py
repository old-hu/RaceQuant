from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup


BASE_URL = "https://racing.hkjc.com/racing/information/English"
LOCAL_BASE_URL = "https://racing.hkjc.com/en-us/local/information"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 RaceQuant/0.1"
)


@dataclass(frozen=True)
class ScrapeResult:
    kind: str
    url: str
    fetched_at: str
    raw_html_path: str
    parsed_json_path: str
    title: str | None
    table_count: int
    text_block_count: int


class HkjcClient:
    def __init__(self, output_dir: Path = Path("data/raw/hkjc"), timeout_seconds: int = 30) -> None:
        self.output_dir = output_dir
        self.timeout_seconds = timeout_seconds

    def race_card_url(self, race_date: str, racecourse: str, race_no: int | None = None) -> str:
        params: dict[str, str | int] = {
            "date": race_date.strip(),
            "venue": racecourse.upper(),
        }
        if race_no is not None:
            params["raceNo"] = race_no
        return f"{LOCAL_BASE_URL}/racecard?{urlencode(params)}"

    def race_result_url(self, race_date: str, racecourse: str, race_no: int | None = None) -> str:
        params: dict[str, str | int] = {
            "RaceDate": normalize_hkjc_date(race_date),
            "Racecourse": racecourse.upper(),
        }
        if race_no is not None:
            params["RaceNo"] = race_no
        return f"{BASE_URL}/Racing/LocalResults.aspx?{urlencode(params)}"

    def race_results_all_url(self, race_date: str) -> str:
        params = {"RaceDate": normalize_hkjc_date(race_date)}
        return f"{BASE_URL}/Racing/ResultsAll.aspx?{urlencode(params)}"

    def race_entries_url(self, race_date: str, racecourse: str) -> str:
        params = {
            "date": race_date.strip(),
            "venue": racecourse.upper(),
            "View": "All",
        }
        return f"{LOCAL_BASE_URL}/entries?{urlencode(params)}"

    def race_changes_url(self, race_date: str) -> str:
        params = {"date": race_date.strip()}
        return f"{LOCAL_BASE_URL}/changes?{urlencode(params)}"

    def horse_url(self, horse_no: str) -> str:
        return f"{BASE_URL}/Horse/Horse.aspx?HorseNo={horse_no.strip().upper()}"

    def scrape_url(self, kind: str, url: str, identity: str) -> ScrapeResult:
        fetched_at = datetime.now().astimezone().isoformat(timespec="seconds")
        html = self.fetch(url)
        parsed = parse_html_tables(html)

        safe_identity = safe_filename(identity)
        target_dir = self.output_dir / kind / safe_identity
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = target_dir / f"{timestamp}.html"
        parsed_path = target_dir / f"{timestamp}.json"

        raw_path.write_text(html, encoding="utf-8")
        parsed_path.write_text(
            json.dumps(
                {
                    "kind": kind,
                    "url": url,
                    "fetched_at": fetched_at,
                    **parsed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        result = ScrapeResult(
            kind=kind,
            url=url,
            fetched_at=fetched_at,
            raw_html_path=str(raw_path),
            parsed_json_path=str(parsed_path),
            title=parsed["title"],
            table_count=len(parsed["tables"]),
            text_block_count=len(parsed["text_blocks"]),
        )

        (target_dir / "latest.json").write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result

    def fetch(self, url: str) -> str:
        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text


def normalize_hkjc_date(value: str) -> str:
    return value.strip().replace("-", "/")


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=-]+", "_", value).strip("_")


def parse_html_tables(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    tables = []
    links = []

    for table_index, table in enumerate(soup.find_all("table"), start=1):
        rows = []
        for tr in table.find_all("tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in tr.find_all(["th", "td"])
                if cell.get_text(" ", strip=True)
            ]
            if cells:
                rows.append(cells)

        if rows:
            tables.append({"index": table_index, "rows": rows})

    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True)
        href = link.get("href", "").strip()
        if text and href:
            links.append({"text": text, "href": href})

    text_blocks = []
    for selector in ["h1", "h2", "h3", "h4", "p", "li", "div"]:
        for node in soup.find_all(selector):
            text = node.get_text(" ", strip=True)
            if 8 <= len(text) <= 500 and text not in text_blocks:
                text_blocks.append(text)
            if len(text_blocks) >= 120:
                break
        if len(text_blocks) >= 120:
            break

    return {"title": title, "tables": tables, "links": links[:200], "text_blocks": text_blocks}
