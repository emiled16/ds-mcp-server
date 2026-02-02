from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.data_science.ds_core.definitions.splitters import Splitter
from src.data_science.feature_store.src.config import Config as FeatureStoreConfig
from src.data_science.regression.metrics import Metric, Scorer
from src.data_science.regression.models import RegressorModel
from src.data_science.regression.models.base import SnowflakeModelClassType
from src.data_science.regression.models.custom import CustomModel


class RunConfig(BaseModel):
    experiment_name: Optional[str] = None
    tracking_uri: Optional[str] = None
    tags: Optional[dict] = None

    input_cols: list[str]
    output_cols: list[str]
    target_cols: list[str]
    model: RegressorModel
    splitter: Splitter
    metrics: list[Metric]
    pipeline: FeatureStoreConfig = Field(default_factory=FeatureStoreConfig)

    def get_model(self) -> SnowflakeModelClassType:
        return self.model.get_model(
            input_cols=self.input_cols,
            output_cols=self.output_cols,
            target_cols=self.target_cols,
        )

    def get_scorer(self) -> Scorer:
        return Scorer(metrics=self.metrics)

    def get_pipeline(self):
        return self.pipeline.generate_pipeline()

    def get_splitter(self):
        return self.splitter

    def get_metrics(self):
        return self.metrics

    def get_custom_model(self):
        return CustomModel(pipeline=self.get_pipeline(), model=self.get_model())
