from typing import Literal

from pydantic import BaseModel

from src.data_science.regression.metrics import Metric


class OptimizeMetricConfig(BaseModel):
    objective: Metric
    direction: Literal["minimize", "maximize"]


class ScoringMetricsConfig(BaseModel):
    to_log: list[Metric]
    to_optimize: OptimizeMetricConfig
    take_last_x_months: int | None = None
