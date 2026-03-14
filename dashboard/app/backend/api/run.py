"""
Experiment Launcher API — WP12
POST /run/launch  — start a new NS-3 experiment
GET  /run/status  — current run state
POST /run/cancel  — cancel active run
GET  /run/history — last 20 launches
"""
import asyncio
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/run", tags=["run"])

# ── Request / Response Models ─────────────────────────────────────────────────

class LaunchRequest(BaseModel):
    scenario: str = Field(..., description="normal | positive | negative")
    seed: int = Field(42, ge=1, le=9999)
    sim_time: float = Field(80.0, ge=10.0, le=600.0)
    bias: float = Field(5000.0)
    num_ap: int = Field(1, ge=1, le=6)
    num_sta: int = Field(2, ge=1, le=12)
    segment_length: int = Field(256, description="32 | 64 | 128 | 256")
    experiment_id: Optional[str] = None   # auto-generated if not provided

    @validator('scenario')
    def validate_scenario(cls, v):
        allowed = {'normal', 'positive', 'negative'}
        if v not in allowed:
            raise ValueError(f"scenario must be one of {allowed}")
        return v

    @validator('segment_length')
    def validate_segment_length(cls, v):
        if v not in {32, 64, 128, 256}:
            raise ValueError("segment_length must be 32, 64, 128, or 256")
        return v

class LaunchResponse(BaseModel):
    ok: bool
    experiment_id: str
    message: str

class RunStatus(BaseModel):
    active: bool
    experiment_id: Optional[str]
    stage: Optional[str]
    state: Optional[str]
    progress_pct: Optional[float]
    message: Optional[str]
    started_at: Optional[str]
    updated_at: Optional[str]

class HistoryEntry(BaseModel):
    experiment_id: str
    scenario: str
    num_ap: int
    num_sta: int
    sim_time: float
    segment_length: int
    started_at: str
    completed_at: Optional[str]
    outcome: str   # "success" | "failed" | "cancelled" | "running"

# ── In-process run state ──────────────────────────────────────────────────────

_active_process: Optional[asyncio.subprocess.Process] = None
_active_exp_id:  Optional[str] = None
_run_history: list = []   # list of HistoryEntry dicts, max 20

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_status_file() -> Optional[str]:
    return os.environ.get("PIPELINE_ACTIVE_STATUS_FILE")

def _read_status_file() -> dict:
    path = _get_status_file()
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}

def _generate_exp_id(scenario: str, num_ap: int, seed: int) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return f"{ts}-{scenario}-{num_ap}ap-seed{seed}"

def _write_status(exp_id: str, stage: str, state: str, message: str = ""):
    path = _get_status_file()
    if not path:
        return
    data = {
        "experiment_id": exp_id,
        "stage": stage,
        "state": state,
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"Could not write status file: {e}")

# ── Background runner ─────────────────────────────────────────────────────────

async def _run_experiment(req: LaunchRequest, exp_id: str):
    global _active_process, _active_exp_id

    # Map scenario names to what run_mlo_scenario.sh expects
    scenario_map = {
        "normal":   "normal",
        "positive": "positive",
        "negative": "negative",
    }
    scenario_arg = scenario_map[req.scenario]

    # Build environment for the subprocess
    env = {
        **os.environ,
        "NAP":      str(req.num_ap),
        "NSTA":     str(req.num_sta),
        "SEED":     str(req.seed),
        "SIM_TIME": str(req.sim_time),
        "BIAS":     str(req.bias),
        # Trigger end-to-end pipeline (streaming mode)
    }

    # Determine repo root (dashboard runs from /app inside container,
    # but run_mlo_scenario.sh lives on the host — use make which is volume-mounted)
    # Use 'make run-mlo-exp-stream' which chains NS-3 → exporter → harmonizer
    cmd = [
        "make", "run-mlo-exp-stream",
        f"EXP_ID={exp_id}",
        f"SCENARIO={scenario_arg}",
        f"NAP={req.num_ap}",
        f"NSTA={req.num_sta}",
        f"SEED={req.seed}",
        f"SIM_TIME={req.sim_time}",
        f"BIAS={req.bias}",
    ]

    log_dir = "/artifacts"
    log_path = os.path.join(log_dir, "last_run.log") if os.path.exists(log_dir) else "/tmp/last_run.log"

    entry = {
        "experiment_id": exp_id,
        "scenario": req.scenario,
        "num_ap": req.num_ap,
        "num_sta": req.num_sta,
        "sim_time": req.sim_time,
        "segment_length": req.segment_length,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "outcome": "running",
    }
    _run_history.insert(0, entry)
    if len(_run_history) > 20:
        _run_history.pop()

    try:
        _write_status(exp_id, "ns3", "active", "Simulation starting…")
        with open(log_path, "w") as log_f:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=log_f,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd="/repo",  # repo root mounted at /repo in container
            )
        _active_process = proc
        returncode = await proc.wait()

        if returncode == 0:
            entry["outcome"] = "success"
            _write_status(exp_id, "db", "idle", "Experiment complete")
        else:
            entry["outcome"] = "failed"
            _write_status(exp_id, "ns3", "error", f"Process exited with code {returncode}")
            logger.error(f"Run {exp_id} failed with code {returncode}")
    except asyncio.CancelledError:
        entry["outcome"] = "cancelled"
        _write_status(exp_id, "ns3", "idle", "Cancelled by user")
        if _active_process:
            try:
                _active_process.terminate()
            except Exception:
                pass
        raise
    except Exception as e:
        entry["outcome"] = "failed"
        _write_status(exp_id, "ns3", "error", str(e))
        logger.exception(f"Run {exp_id} crashed: {e}")
    finally:
        entry["completed_at"] = datetime.now(timezone.utc).isoformat()
        _active_process = None
        _active_exp_id = None

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/launch", response_model=LaunchResponse)
async def launch_experiment(req: LaunchRequest, request: Request):
    global _active_exp_id

    # Prevent concurrent runs
    if _active_process is not None and _active_process.returncode is None:
        raise HTTPException(
            status_code=409,
            detail="A run is already active. Cancel it first or wait for it to complete."
        )

    exp_id = req.experiment_id or _generate_exp_id(req.scenario, req.num_ap, req.seed)
    _active_exp_id = exp_id

    # Fire and forget — run in background
    asyncio.get_event_loop().create_task(_run_experiment(req, exp_id))

    logger.info(f"Launched experiment {exp_id}")
    return LaunchResponse(ok=True, experiment_id=exp_id, message="Experiment launched")


@router.get("/status", response_model=RunStatus)
async def get_run_status():
    file_status = _read_status_file()

    is_active = _active_process is not None and (
        _active_process.returncode is None
    )

    return RunStatus(
        active=is_active,
        experiment_id=_active_exp_id or file_status.get("experiment_id"),
        stage=file_status.get("stage"),
        state=file_status.get("state"),
        progress_pct=None,  # future: parse log for progress
        message=file_status.get("message"),
        started_at=None,
        updated_at=file_status.get("updated_at"),
    )


@router.post("/cancel")
async def cancel_run():
    global _active_process
    if _active_process is None or _active_process.returncode is not None:
        raise HTTPException(status_code=404, detail="No active run to cancel")
    try:
        _active_process.terminate()
        return {"ok": True, "message": "Termination signal sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_run_history():
    return {"history": _run_history}
