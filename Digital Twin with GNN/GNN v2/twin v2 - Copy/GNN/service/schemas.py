# GNN/service/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class BackoffEvent(BaseModel):
    timestamp: float
    node_id: int
    link_id: int
    frequency: float
    channel_width: int
    mcs: int
    guard_interval: int
    cw_min: int
    cw_max: int
    backoff_value: int

class PredictRequest(BaseModel):
    experiment_id: str = Field(..., examples=["exp_001"])
    window_s: float = Field(0.1, description="Window size in seconds used to aggregate events")
    window_events: List[BackoffEvent]

class PredictResponse(BaseModel):
    model_version: str
    attack_probability: float
