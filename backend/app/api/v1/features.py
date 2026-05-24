from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.core.config import settings
from app.quant.features.engine import FeatureEngine


router = APIRouter(prefix="/features", tags=["features"])
OddsMode = Literal["none", "pre_start_latest", "result_final"]


@router.get("/runner-features")
def list_runner_features(
    race_date: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    racecourse: Annotated[str | None, Query(pattern=r"^(HV|ST|hv|st)$")] = None,
    race_no: Annotated[int | None, Query(ge=1, le=20)] = None,
    odds_mode: OddsMode = "none",
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> dict[str, object]:
    db_path = Path(settings.hkjc_structured_db_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[4] / db_path
    odds_db_path = Path(settings.legacy_odds_db_path)
    if not odds_db_path.is_absolute():
        odds_db_path = Path(__file__).resolve().parents[4] / odds_db_path
    rows = FeatureEngine(db_path, odds_mode=odds_mode, odds_db_path=odds_db_path).build_runner_features(
        race_date=race_date,
        racecourse=racecourse,
        race_no=race_no,
        limit=limit,
    )
    return {"items": [asdict(row) for row in rows]}
