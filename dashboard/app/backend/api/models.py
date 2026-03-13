from fastapi import APIRouter, Request, HTTPException
from ..db import queries
from ..registry import reader

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
async def list_models(request: Request):
    registry_path = reader.get_registry_path()
    versions = reader.list_versions(registry_path)
    active = reader.get_active_version(registry_path)
    result = []
    for v in versions:
        info = reader.read_version(registry_path, v)
        result.append(
            {
                "version": v,
                "is_active": v == active,
                "created": info.get("created"),
                "dataset": info.get("dataset"),
                "scenarios": info.get("scenarios"),
                "has_test_results": info.get("has_test_results", False),
            }
        )
    return {"models": result, "active_version": active}


@router.get("/active")
async def get_active_model(request: Request):
    registry_path = reader.get_registry_path()
    active = reader.get_active_version(registry_path)
    if not active:
        raise HTTPException(status_code=404, detail="No active model found")
    info = reader.read_version(registry_path, active)
    return {
        "version": active,
        "created": info.get("created"),
        "dataset": info.get("dataset"),
        "scenarios": info.get("scenarios"),
        "distribution": info.get("distribution"),
        "architecture": info.get("architecture"),
        "test_results": info.get("test_results"),
    }


@router.get("/inference-stats")
async def inference_stats(request: Request):
    row = await queries.get_inference_stats(request.app.state.pool)
    if not row or not row["count"]:
        return {
            "count": 0,
            "min_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
            "avg_ms": None,
        }
    return {
        "count": row["count"],
        "min_ms": float(row["min_ms"]) if row["min_ms"] else None,
        "p50_ms": float(row["p50_ms"]) if row["p50_ms"] else None,
        "p95_ms": float(row["p95_ms"]) if row["p95_ms"] else None,
        "max_ms": float(row["max_ms"]) if row["max_ms"] else None,
        "avg_ms": float(row["avg_ms"]) if row["avg_ms"] else None,
    }


@router.get("/{version}/test_results")
async def model_test_results(request: Request, version: str):
    registry_path = reader.get_registry_path()
    info = reader.read_version(registry_path, version)
    if not info.get("has_test_results"):
        raise HTTPException(
            status_code=404, detail="No test_results.json found for this version"
        )
    return info.get("test_results")
