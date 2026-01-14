# GNN/service/schemas.py
from pydantic import BaseModel
from typing import List

class NodeDef(BaseModel):
    id: str
    type: str  # "AP" or "STA"

class EdgeDef(BaseModel):
    src: str
    dst: str

class Topology(BaseModel):
    nodes: List[NodeDef]
    edges: List[EdgeDef]

class NodeFeatures(BaseModel):
    node_id: str
    node_type: str

    event_count: float
    mean_backoff: float
    std_backoff: float
    p95_backoff: float
    max_backoff: float
    mean_norm: float
    p95_norm: float
    cw_min: float
    cw_max: float
    mcs: float
    channel_width: float
    guard_interval: float
    frequency: float

class PredictRequest(BaseModel):
    experiment_id: str
    topology: Topology
    features: List[NodeFeatures]

class PredictResponse(BaseModel):
    model_version: str
    attack_probability: float
