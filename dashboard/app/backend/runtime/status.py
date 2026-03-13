import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TypedDict


class RuntimeStatus(TypedDict):
    experiment_id: Optional[str]
    stage: str
    state: str
    ns3_windows: int
    metrics_count: int
    updated_at: datetime


ACTIVE_STATUS_FILE = os.getenv("PIPELINE_ACTIVE_STATUS_FILE", "/artifacts/.pipeline_active.json")
MAX_AGE_SECONDS = int(os.getenv("PIPELINE_RUNTIME_MAX_AGE_SEC", "15"))


def _parse_iso_utc(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _read_json(path: Path) -> Optional[dict]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def read_active_runtime_status() -> Optional[RuntimeStatus]:
    payload = _read_json(Path(ACTIVE_STATUS_FILE))
    if not payload:
        return None

    updated_at = _parse_iso_utc(payload.get("updated_at"))
    if not updated_at:
        return None

    age = (datetime.now(timezone.utc) - updated_at).total_seconds()
    if age > MAX_AGE_SECONDS:
        return None

    return RuntimeStatus(
        experiment_id=payload.get("experiment_id"),
        stage=str(payload.get("stage", "unknown")),
        state=str(payload.get("state", "idle")),
        ns3_windows=int(payload.get("ns3_windows", 0) or 0),
        metrics_count=int(payload.get("metrics_count", 0) or 0),
        updated_at=updated_at,
    )

