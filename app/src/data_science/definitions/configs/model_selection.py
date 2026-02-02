from typing import Literal

from pydantic import BaseModel

from src.data_science.regression.metrics import Metric


class ModelSelectionPipelineConfig(BaseModel):
    experiment_id: str | None = None
    feature_store_id: str | None = None
    objective: Metric
    direction: Literal["minimize", "maximize"]
