from fastapi import APIRouter, Request
from datetime import datetime, timezone
from ..db import queries

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/status")
async def pipeline_status(request: Request):
    stages, latest_exp = await queries.get_pipeline_status(request.app.state.pool)
    return {
        "stages": {
            k: {
                **v,
                "last_activity_ts": (
                    v["last_activity_ts"].isoformat() if v.get("last_activity_ts") else None
                ),
            }
            for k, v in stages.items()
        },
        "latest_experiment_id": latest_exp,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
