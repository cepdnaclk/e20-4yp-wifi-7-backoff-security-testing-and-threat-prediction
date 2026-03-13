from fastapi import APIRouter, Request, Query
from ..db import queries

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/summary")
async def analysis_summary(request: Request):
    row = await queries.get_analysis_summary(request.app.state.pool)
    if not row or not row["total_segments"]:
        return {
            "total_segments": 0,
            "total_attacks": 0,
            "total_normals": 0,
            "tp": 0,
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "precision": None,
            "recall": None,
            "f1": None,
            "fpr": None,
            "fnr": None,
            "accuracy": None,
        }
    tp = row["tp"] or 0
    tn = row["tn"] or 0
    fp = row["fp"] or 0
    fn = row["fn"] or 0
    total = row["total_segments"] or 0
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else None
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else None
    fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else None
    fnr = round(fn / (fn + tp), 4) if (fn + tp) > 0 else None
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision and recall and (precision + recall) > 0) else None
    accuracy = round((tp + tn) / total, 4) if total > 0 else None
    return {
        "total_segments": total,
        "total_attacks": row["total_attacks"] or 0,
        "total_normals": row["total_normals"] or 0,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
        "fnr": fnr,
        "accuracy": accuracy,
    }


@router.get("/confidence-histogram")
async def confidence_histogram(request: Request, bins: int = Query(10, le=20)):
    rows = await queries.get_confidence_histogram(request.app.state.pool, bins)
    step = 1.0 / bins
    normal_bins: list = []
    attack_bins: list = []
    normal_counts = [0] * bins
    attack_counts = [0] * bins
    for r in rows:
        idx = (r["bin_idx"] or 1) - 1
        idx = max(0, min(idx, bins - 1))
        if r["prediction"] == 0:
            normal_counts[idx] += r["cnt"]
        else:
            attack_counts[idx] += r["cnt"]
    for i in range(bins):
        bin_start = round(i * step, 2)
        bin_end = round((i + 1) * step, 2)
        normal_bins.append({"bin_start": bin_start, "bin_end": bin_end, "count": normal_counts[i]})
        attack_bins.append({"bin_start": bin_start, "bin_end": bin_end, "count": attack_counts[i]})
    return {"normal": normal_bins, "attack": attack_bins}


@router.get("/attack-by-type")
async def attack_by_type(request: Request):
    rows = await queries.get_attack_by_type(request.app.state.pool)
    groups = []
    for r in rows:
        total = r["total_segments"] or 0
        attacks = r["attack_segments"] or 0
        detection_rate = round(attacks / total, 4) if total > 0 else 0.0
        groups.append({
            "exp_type": r["exp_type"],
            "total_segments": total,
            "attack_segments": attacks,
            "detection_rate": detection_rate,
        })
    return {"groups": groups}
