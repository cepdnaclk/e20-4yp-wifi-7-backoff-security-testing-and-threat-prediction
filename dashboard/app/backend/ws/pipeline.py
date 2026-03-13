import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..db import queries

router = APIRouter()
POLL_INTERVAL = 0.5  # seconds
BACKFILL_EVENTS = 20


@router.websocket("/ws/pipeline")
async def websocket_pipeline(websocket: WebSocket):
    await websocket.accept()
    pool = websocket.app.state.pool
    last_pred_id = 0

    # Send connection ack
    await websocket.send_json(
        {
            "type": "connection_ack",
            "ts": datetime.now(timezone.utc).isoformat(),
            "server_version": "1.0.0",
            "message": "Connected to NDT pipeline monitor",
        }
    )

    # Initialize with a short backfill so activity feed is not empty on reconnect.
    try:
        async with pool.acquire() as conn:
            max_pred_id = (
                await conn.fetchval("SELECT COALESCE(MAX(id), 0) FROM gcn_predictions") or 0
            )
            last_pred_id = max(0, int(max_pred_id) - BACKFILL_EVENTS)
    except Exception:
        pass

    try:
        while True:
            await asyncio.sleep(POLL_INTERVAL)

            # Send pipeline_status
            try:
                stages, latest_exp = await queries.get_pipeline_status(pool)
                status_msg = {
                    "type": "pipeline_status",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "stages": {
                        k: {
                            **v,
                            "last_activity_ts": (
                                v["last_activity_ts"].isoformat()
                                if v.get("last_activity_ts")
                                else None
                            ),
                        }
                        for k, v in stages.items()
                    },
                    "latest_experiment_id": latest_exp,
                }
                await websocket.send_json(status_msg)
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

            # Poll for new predictions and emit events
            try:
                new_preds = await queries.get_new_predictions(
                    pool,
                    last_pred_id,
                    experiment_id=latest_exp,
                    limit=100,
                )
                for pred in new_preds:
                    label = "ATTACK" if pred["prediction"] == 1 else "NORMAL"
                    conf = float(pred["confidence"])
                    seg_id = pred["segment_id"] or ""
                    event = {
                        "type": "pipeline_event",
                        "ts": (
                            pred["created_at"].isoformat()
                            if pred["created_at"]
                            else datetime.now(timezone.utc).isoformat()
                        ),
                        "stage": "gcn",
                        "level": "warning" if pred["prediction"] == 1 else "info",
                        "message": f"{seg_id} -> {label}  conf={conf:.3f}",
                        "experiment_id": pred["experiment_id"],
                        "prediction": pred["prediction"],
                        "confidence": conf,
                    }
                    await websocket.send_json(event)
                    last_pred_id = max(last_pred_id, pred["id"])
            except Exception:
                pass

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
