from pydantic import BaseModel
from typing import Dict, List, Optional, Any

class NodeFeature(BaseModel):
    node_id: str
    node_type: str
    f_throughput_hint: float
    f_delay_hint: float
    f_retry_hint: float

class PredictRequest(BaseModel):
    experiment_id: str
    topology: Dict[str, Any]
    features: List[NodeFeature]

class Prediction(BaseModel):
    node_id: Optional[str]
    kpi_name: str
    value: float

class PredictResponse(BaseModel):
    model_version: str
    predictions: List[Prediction]
