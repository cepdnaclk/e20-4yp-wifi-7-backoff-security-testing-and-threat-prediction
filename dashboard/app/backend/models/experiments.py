from pydantic import BaseModel
from typing import Optional, List


class ExperimentSummary(BaseModel):
    experiment_id: str
    inferred_type: str
    first_ts: Optional[str]
    last_ts: Optional[str]
    metric_count: int
    segment_count: int
    attack_segment_count: int
    normal_segment_count: int
    attack_rate: float
    avg_confidence: Optional[float]
    model_version: Optional[str]
    pass_fail: str


class ExperimentPrediction(BaseModel):
    id: int
    segment_id: Optional[str]
    segment_number: int
    prediction: int
    prediction_label: str
    confidence: float
    p_normal: Optional[float]
    p_attack: Optional[float]
    window_start_idx: Optional[int]
    window_end_idx: Optional[int]
    ts_start: Optional[str]
    ts_end: Optional[str]
    inference_time_ms: Optional[float]


class MetricPoint(BaseModel):
    ts: str
    value: float


class MetricSeries(BaseModel):
    experiment_id: str
    metric_name: str
    entity_id: str
    unit: str
    points: List[MetricPoint]


class MetricStatRow(BaseModel):
    metric_name: str
    unit: Optional[str]
    avg: float
    min: float
    max: float
    std: float
    trend: str


class ExperimentListResponse(BaseModel):
    experiments: List[ExperimentSummary]
    total: int
    limit: int
    offset: int
