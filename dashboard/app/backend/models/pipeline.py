from pydantic import BaseModel
from typing import Optional, Dict


class StageStatus(BaseModel):
    state: str
    counter: int
    label: str
    last_activity_ts: Optional[str]


class PipelineStatusResponse(BaseModel):
    stages: Dict[str, StageStatus]
    latest_experiment_id: Optional[str]
    last_updated: str


class WebSocketConnectionAck(BaseModel):
    type: str
    ts: str
    server_version: str
    message: str


class WebSocketPipelineEvent(BaseModel):
    type: str
    ts: str
    stage: str
    level: str
    message: str
    experiment_id: Optional[str]
    prediction: Optional[int]
    confidence: Optional[float]
