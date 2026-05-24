from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.services import odds_repository


router = APIRouter(prefix="/odds", tags=["odds"])

OddsType = Literal["win", "fct", "qin", "qpl"]


@router.post("/import-legacy")
def import_legacy_odds_status() -> dict[str, object]:
    return {
        "status": "ready",
        "message": "旧赔率数据已迁移到本地 SQLite，当前接口返回导入状态。",
        "summary": odds_repository.get_import_status(),
    }


@router.get("/snapshots")
def list_odds_snapshots(
    race_date: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    race_no: Annotated[int | None, Query(ge=1)] = None,
    odds_type: OddsType | None = None,
    odds_value: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    return {
        "items": odds_repository.list_snapshots(
            race_date=race_date,
            race_no=race_no,
            odds_type=odds_type,
            odds_value=odds_value,
            limit=limit,
            offset=offset,
        )
    }


@router.get("/summary")
def summarize_odds_snapshots(
    race_date: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    race_no: Annotated[int | None, Query(ge=1)] = None,
) -> dict[str, object]:
    return {"items": odds_repository.summarize_snapshots(race_date=race_date, race_no=race_no)}


@router.get("/changes")
def list_odds_changes(
    race_date: Annotated[str, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    race_no: Annotated[int, Query(ge=1)],
    odds_type: OddsType = "win",
    odds_value: str | None = None,
    limit_values: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, object]:
    return {
        "items": odds_repository.list_changes(
            race_date=race_date,
            race_no=race_no,
            odds_type=odds_type,
            odds_value=odds_value,
            limit_values=limit_values,
        )
    }
