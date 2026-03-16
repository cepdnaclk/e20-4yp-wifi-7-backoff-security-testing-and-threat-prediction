import socket
from fastapi import APIRouter, Request, HTTPException
from ..db import queries
from ..registry import reader

router = APIRouter(prefix="/models", tags=["models"])


def _docker_restart(container_name: str) -> bool:
    """Restart a Docker container via the unix socket — no docker CLI needed."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect("/var/run/docker.sock")
        req = (
            f"POST /containers/{container_name}/restart HTTP/1.0\r\n"
            f"Host: localhost\r\n"
            f"Content-Length: 0\r\n\r\n"
        )
        sock.sendall(req.encode())
        resp = sock.recv(256).decode(errors="ignore")
        sock.close()
        return "204" in resp or "200" in resp
    except Exception:
        return False


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
                "is_current": v == active,
                "created": info.get("created"),
                "dataset": info.get("dataset"),
                "scenarios": info.get("scenarios"),
                "has_test_results": info.get("has_test_results", False),
                "test_results": info.get("test_results"),
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


@router.get("/{version}")
async def get_model_version(version: str):
    registry_path = reader.get_registry_path()
    versions = reader.list_versions(registry_path)
    if version not in versions:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    active = reader.get_active_version(registry_path)
    info = reader.read_version(registry_path, version)
    return {
        "version": version,
        "is_active": version == active,
        "created": info.get("created"),
        "dataset": info.get("dataset"),
        "scenarios": info.get("scenarios"),
        "distribution": info.get("distribution"),
        "architecture": info.get("architecture"),
        "test_results": info.get("test_results"),
    }


@router.post("/{version}/deploy")
async def deploy_model(version: str, restart_detector: bool = True):
    registry_path = reader.get_registry_path()
    versions = reader.list_versions(registry_path)
    if version not in versions:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")

    # Update the current symlink
    current_link = registry_path / "current"
    try:
        if current_link.is_symlink() or current_link.exists():
            current_link.unlink()
        current_link.symlink_to(version)
    except PermissionError:
        raise HTTPException(
            status_code=500,
            detail="Cannot update registry symlink — /registry is mounted read-only",
        )

    restarted = False
    if restart_detector:
        restarted = _docker_restart("ndt-pipeline-gcn-detector")

    return {
        "deployed": version,
        "detector_restarted": restarted,
        "message": (
            "Model deployed and detector restarted."
            if restarted
            else "Model deployed. Restart ndt-pipeline-gcn-detector to apply."
        ),
    }


@router.get("/{version}/test_results")
async def model_test_results(version: str):
    registry_path = reader.get_registry_path()
    info = reader.read_version(registry_path, version)
    if not info.get("has_test_results"):
        raise HTTPException(
            status_code=404, detail="No test_results.json found for this version"
        )
    return info.get("test_results")
