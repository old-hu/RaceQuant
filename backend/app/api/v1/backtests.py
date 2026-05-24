from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.services import backtest_repository


router = APIRouter(prefix="/backtests", tags=["backtests"])


class BacktestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    strategyName: str = Field(min_length=1, max_length=64)
    parameters: dict[str, Any] = Field(default_factory=dict)
    execute: bool = True


@router.post("")
def create_backtest(payload: BacktestCreate) -> dict[str, object]:
    return backtest_repository.create_run(payload.name, payload.strategyName, payload.parameters, execute=payload.execute)


@router.get("")
def list_backtests(
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    return {"items": backtest_repository.list_runs(limit=limit, offset=offset)}


@router.get("/{run_id}")
def get_backtest(run_id: Annotated[int, Path(ge=1)]) -> dict[str, object]:
    run = backtest_repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return run


@router.get("/{run_id}/results")
def get_backtest_results(run_id: Annotated[int, Path(ge=1)]) -> dict[str, object]:
    results = backtest_repository.get_results(run_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return results


@router.post("/{run_id}/run")
def run_backtest(run_id: Annotated[int, Path(ge=1)]) -> dict[str, object]:
    run = backtest_repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return backtest_repository.run_backtest(run_id)
