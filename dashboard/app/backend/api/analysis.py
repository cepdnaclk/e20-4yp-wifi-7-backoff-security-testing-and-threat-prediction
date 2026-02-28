from fastapi import APIRouter, Request, Query
from ..db import queries

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/summary")
async def analysis_summary(request: Request):
    row = await queries.get_analysis_summary(request.app.state.pool)
    if not row or not row["total_segments"]:
        return {
            "total_segments": 0,
            "attack_segments": 0,
            "normal_segments": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_positives": 0,
            "true_negatives": 0,
            "precision": None,
            "recall": None,
            "fpr": None,
            "fnr": None,
        }
    tp = row["tp"] or 0
    tn = row["tn"] or 0
    fp = row["fp"] or 0
    fn = row["fn"] or 0
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else None
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else None
    fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else None
    fnr = round(fn / (fn + tp), 4) if (fn + tp) > 0 else None
    return {
        "total_segments": row["total_segments"],
        "attack_segments": row["total_attacks"] or 0,
        "normal_segments": row["total_normals"] or 0,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "true_negatives": tn,
        "precision": precision,
        "recall": recall,
        "fpr": fpr,
        "fnr": fnr,
    }


@router.get("/confidence_histogram")
async def confidence_histogram(request: Request, bins: int = Query(10, le=20)):
    rows = await queries.get_confidence_histogram(request.app.state.pool, bins)
    step = 1.0 / bins
    bin_edges = [round(i * step, 2) for i in range(bins + 1)]
    normal_counts = [0] * bins
    attack_counts = [0] * bins
    for r in rows:
        idx = (r["bin_idx"] or 1) - 1
        idx = max(0, min(idx, bins - 1))
        if r["prediction"] == 0:
            normal_counts[idx] += r["cnt"]
        else:
            attack_counts[idx] += r["cnt"]
    return {"bins": bin_edges, "normal_counts": normal_counts, "attack_counts": attack_counts}


@router.get("/by_experiment_type")
async def attack_by_type(request: Request):
    rows = await queries.get_attack_by_type(request.app.state.pool)
    return {
        "groups": [
            {
                "type": r["exp_type"],
                "total_segments": r["total_segments"],
                "attack_segments": r["attack_segments"],
            }
            for r in rows
        ]
    }
