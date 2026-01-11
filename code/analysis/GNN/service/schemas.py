# GNN/service/schemas.py
from pydantic import BaseModel, Field
from typing import List

class WindowFeatures(BaseModel):
    window: int
    bias: float

    net_throughput_mbps: float
    net_avg_delay_ms: float
    net_avg_jitter_ms: float
    net_packet_loss_ratio: float
    net_active_flows: float

    mac_total_tx: float
    mac_total_rx: float
    mac_total_ack: float
    mac_total_retrans: float
    mac_drop_count: float

    phy_drop_count: float

    avg_backoff_slots: float
    channel_busy_ratio: float

class PredictRequest(BaseModel):
    experiment_id: str = Field(..., examples=["exp_001"])
    windows: List[WindowFeatures]

class PredictResponse(BaseModel):
    model_version: str
    predicted_class: int
    probabilities: List[float]
