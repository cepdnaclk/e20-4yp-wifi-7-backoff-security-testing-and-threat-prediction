from pydantic import BaseModel
from typing import Optional, Any, Dict


class ModelArchitecture(BaseModel):
    in_channels: int
    hidden_channels: int
    num_layers: int
    dropout: float
    pooling: str
    segment_length: int
    batch_size: int


class ModelInfo(BaseModel):
    version: str
    is_active: bool
    created: Optional[str]
    dataset: Optional[str]
    scenarios: Optional[Any]
    has_test_results: bool


class ActiveModelDetail(BaseModel):
    version: str
    created: Optional[str]
    dataset: Optional[str]
    scenarios: Optional[Any]
    distribution: Optional[str]
    architecture: Optional[ModelArchitecture]
    test_results: Optional[Dict[str, Any]]


class InferenceStats(BaseModel):
    count: int
    min_ms: Optional[float]
    p50_ms: Optional[float]
    p95_ms: Optional[float]
    max_ms: Optional[float]
    avg_ms: Optional[float]


class ModelListResponse(BaseModel):
    models: list[ModelInfo]
    active_version: Optional[str]
