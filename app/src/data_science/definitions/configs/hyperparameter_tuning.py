from pydantic import BaseModel

from src.data_science.definitions.configs.components.metrics import ScoringMetricsConfig
from src.data_science.definitions.configs.components.mlflow_logging import RunConfig
from src.data_science.definitions.configs.components.runs import RunsConfig
from src.data_science.definitions.configs.components.schema import SchemaConfig
from src.data_science.regression.models import RegressorGridSearchConfig


class HyperparameterTuningPipelineConfig(BaseModel):
    runs: RunsConfig
    schema: SchemaConfig
    models: list[RegressorGridSearchConfig]
    scoring_metrics: ScoringMetricsConfig

    def to_run_config(self) -> RunConfig:
        return RunConfig(
            input_cols=self.schema.features.mandatory + self.schema.features.optional,
            output_cols=[self.schema.target],
            target_cols=[self.schema.target],
        )
