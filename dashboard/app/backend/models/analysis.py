from pydantic import BaseModel
from typing import Optional, List


class AnalysisSummary(BaseModel):
    total_segments: int
    attack_segments: int
    normal_segments: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: Optional[float]
    recall: Optional[float]
    fpr: Optional[float]
    fnr: Optional[float]


class ConfidenceHistogram(BaseModel):
    bins: List[float]
    normal_counts: List[int]
    attack_counts: List[int]


class ExperimentTypeGroup(BaseModel):
    type: str
    total_segments: int
    attack_segments: int


class AttackByTypeResponse(BaseModel):
    groups: List[ExperimentTypeGroup]
