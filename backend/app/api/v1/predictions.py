from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.services import prediction_repository


router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("")
def list_predictions(
    race_date: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    racecourse: Annotated[str | None, Query(pattern=r"^(HV|ST|hv|st)$")] = None,
    race_no: Annotated[int | None, Query(ge=1, le=20)] = None,
    model_name: str | None = None,
) -> dict[str, object]:
    return {
        "items": prediction_repository.list_predictions(
            race_date=race_date,
            racecourse=racecourse,
            race_no=race_no,
            model_name=model_name,
        )
    }
