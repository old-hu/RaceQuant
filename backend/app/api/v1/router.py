from fastapi import APIRouter

from app.api.v1.backtests import router as backtests_router
from app.api.v1.features import router as features_router
from app.api.v1.odds import router as odds_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.racing import router as racing_router

router = APIRouter()


@router.get("/health", tags=["health"])
def api_health_check() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(odds_router)
router.include_router(predictions_router)
router.include_router(backtests_router)
router.include_router(features_router)
router.include_router(racing_router)

api_router = router
