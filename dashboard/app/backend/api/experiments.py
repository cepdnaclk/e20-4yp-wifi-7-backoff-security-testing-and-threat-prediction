from fastapi import APIRouter, Request, Query, HTTPException
from typing import Optional
from ..db import queries

router = APIRouter(prefix="/experiments", tags=["experiments"])


def infer_type(experiment_id: str) -> str:
    eid = experiment_id.lower()
    if "normal" in eid:
        return "normal"
    if "attack" in eid or "positive" in eid or "negative" in eid:
        return "attack"
    return "unknown"


def pass_fail(exp_type: str, attack_rate: float) -> str:
    if exp_type == "normal":
        return "pass" if attack_rate < 0.1 else "fail"
    elif exp_type == "attack":
        return "pass" if attack_rate > 0.9 else "fail"
    return "unknown"


@router.get("")
async def list_experiments(
    request: Request,
    limit: int = Query(50, le=200),
    offset: int = 0,
    prefix: Optional[str] = None,
):
    rows = await queries.get_experiments(request.app.state.pool, limit, offset, prefix)
    total = await queries.count_experiments(request.app.state.pool, prefix)
    result = []
    for r in rows:
        seg = r["segment_count"] or 0
        atk = r["attack_segments"] or 0
        rate = round(atk / seg, 4) if seg > 0 else 0.0
        exp_type = infer_type(r["experiment_id"])
        result.append(
            {
                "experiment_id": r["experiment_id"],
                "inferred_type": exp_type,
                "first_ts": r["first_ts"].isoformat() if r["first_ts"] else None,
                "last_ts": r["last_ts"].isoformat() if r["last_ts"] else None,
                "metric_count": r["metric_count"],
                "segment_count": seg,
                "attack_segment_count": atk,
                "normal_segment_count": seg - atk,
                "attack_rate": rate,
                "avg_confidence": float(r["avg_confidence"]) if r["avg_confidence"] else None,
                "model_version": r["model_version"],
                "pass_fail": pass_fail(exp_type, rate),
            }
        )
    return {"experiments": result, "total": total, "limit": limit, "offset": offset}


@router.get("/{experiment_id}/summary")
async def experiment_summary(request: Request, experiment_id: str):
    row = await queries.get_experiment_summary(request.app.state.pool, experiment_id)
    if not row or row["segment_count"] == 0:
        return {
            "experiment_id": experiment_id,
            "segment_count": 0,
            "attack_segment_count": 0,
            "normal_segment_count": 0,
            "attack_rate": 0.0,
            "avg_confidence": None,
            "min_confidence": None,
            "max_confidence": None,
            "avg_inference_time_ms": None,
            "model_version": None,
            "ts_start": None,
            "ts_end": None,
        }
    seg = row["segment_count"] or 0
    atk = row["attack_segments"] or 0
    return {
        "experiment_id": experiment_id,
        "segment_count": seg,
        "attack_segment_count": atk,
        "normal_segment_count": row["normal_segments"] or 0,
        "attack_rate": round(atk / seg, 4) if seg > 0 else 0.0,
        "avg_confidence": float(row["avg_confidence"]) if row["avg_confidence"] else None,
        "min_confidence": float(row["min_confidence"]) if row["min_confidence"] else None,
        "max_confidence": float(row["max_confidence"]) if row["max_confidence"] else None,
        "avg_inference_time_ms": float(row["avg_inference_ms"]) if row["avg_inference_ms"] else None,
        "model_version": row["model_version"],
        "ts_start": row["ts_start"].isoformat() if row["ts_start"] else None,
        "ts_end": row["ts_end"].isoformat() if row["ts_end"] else None,
    }


@router.get("/{experiment_id}/predictions")
async def experiment_predictions(request: Request, experiment_id: str):
    rows = await queries.get_experiment_predictions(request.app.state.pool, experiment_id)
    predictions = []
    for i, r in enumerate(rows):
        predictions.append(
            {
                "id": r["id"],
                "segment_id": r["segment_id"],
                "segment_number": i + 1,
                "prediction": r["prediction"],
                "prediction_label": "attack" if r["prediction"] == 1 else "normal",
                "confidence": float(r["confidence"]),
                "p_normal": float(r["p_normal"]) if r["p_normal"] else None,
                "p_attack": float(r["p_attack"]) if r["p_attack"] else None,
                "window_start_idx": r["window_start_idx"],
                "window_end_idx": r["window_end_idx"],
                "ts_start": r["ts_start"].isoformat() if r["ts_start"] else None,
                "ts_end": r["ts_end"].isoformat() if r["ts_end"] else None,
                "inference_time_ms": float(r["inference_time_ms"]) if r["inference_time_ms"] else None,
            }
        )
    return {"predictions": predictions}


@router.get("/{experiment_id}/metrics")
async def experiment_metrics(
    request: Request,
    experiment_id: str,
    metric: str = Query(...),
    entity_id: Optional[str] = None,
    downsample: int = Query(500, le=2000),
):
    rows, unit = await queries.get_experiment_metric_series(
        request.app.state.pool, experiment_id, metric, entity_id, downsample
    )
    points = [{"ts": r["ts"].isoformat(), "value": float(r["value"])} for r in rows]
    eid = rows[0]["entity_id"] if rows else (entity_id or "network")
    return {
        "experiment_id": experiment_id,
        "metric_name": metric,
        "entity_id": eid,
        "unit": unit,
        "points": points,
    }


@router.get("/{experiment_id}/metrics/summary")
async def experiment_metrics_summary(request: Request, experiment_id: str):
    rows = await queries.get_experiment_metrics_summary(request.app.state.pool, experiment_id)
    metrics = []
    for r in rows:
        avg = float(r["avg_val"]) if r["avg_val"] else 0
        mn = float(r["min_val"]) if r["min_val"] else 0
        mx = float(r["max_val"]) if r["max_val"] else 0
        std = float(r["std_val"]) if r["std_val"] else 0
        trend = "flat"
        if std > 0:
            trend = "up" if avg > (mn + mx) / 2 else "down"
        metrics.append(
            {
                "metric_name": r["metric_name"],
                "unit": r["unit"],
                "avg": avg,
                "min": mn,
                "max": mx,
                "std": std,
                "trend": trend,
            }
        )
    return {"experiment_id": experiment_id, "metrics": metrics}
