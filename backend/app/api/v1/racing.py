from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.services import hkjc_repository


router = APIRouter(prefix="/racing", tags=["racing"])


@router.get("/races")
def list_races(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    return {"items": hkjc_repository.list_races(limit=limit, offset=offset)}


@router.get("/races/{race_date}/{racecourse}/{race_no}")
def get_race(
    race_date: Annotated[str, Path(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    racecourse: Annotated[str, Path(pattern=r"^(HV|ST|hv|st)$")],
    race_no: Annotated[int, Path(ge=1, le=20)],
) -> dict[str, object]:
    race = hkjc_repository.get_race(race_date, racecourse, race_no)
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    return race


@router.get("/races/{race_date}/{racecourse}/{race_no}/runners")
def list_race_runners(
    race_date: Annotated[str, Path(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    racecourse: Annotated[str, Path(pattern=r"^(HV|ST|hv|st)$")],
    race_no: Annotated[int, Path(ge=1, le=20)],
) -> dict[str, object]:
    return {"items": hkjc_repository.list_race_runners(race_date, racecourse, race_no)}


@router.get("/races/{race_date}/{racecourse}/{race_no}/entries")
def list_race_entries(
    race_date: Annotated[str, Path(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    racecourse: Annotated[str, Path(pattern=r"^(HV|ST|hv|st)$")],
    race_no: Annotated[int, Path(ge=1, le=20)],
) -> dict[str, object]:
    return {"items": hkjc_repository.list_race_entries(race_date, racecourse, race_no)}


@router.get("/changes")
def list_change_events(
    race_date: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    race_no: Annotated[int | None, Query(ge=1, le=20)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    return {"items": hkjc_repository.list_change_events(race_date=race_date, race_no=race_no, limit=limit, offset=offset)}


@router.get("/horses/{horse_code}")
def get_horse(horse_code: Annotated[str, Path(pattern=r"^[A-Za-z]\d{3}$")]) -> dict[str, object]:
    horse = hkjc_repository.get_horse(horse_code)
    if horse is None:
        raise HTTPException(status_code=404, detail="Horse not found")
    return horse


@router.get("/horses/{horse_code}/history")
def list_horse_history(
    horse_code: Annotated[str, Path(pattern=r"^[A-Za-z]\d{3}$")],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    return {"items": hkjc_repository.list_horse_history(horse_code, limit=limit, offset=offset)}
