import uuid

from pydantic import BaseModel, Field

from src.data_science.definitions.configs.components.data import ExperimentPipelineDataConfig
from src.data_science.definitions.configs.components.experiments import ExperimentsConfig
from src.data_science.definitions.configs.components.splitter import SplitterConfig
from src.data_science.definitions.configs.components.timeseries import TimeSeriesConfig


class ExperimentPipelineConfig(BaseModel):
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: ExperimentPipelineDataConfig
    time_series: TimeSeriesConfig
    experiments: ExperimentsConfig
    splitters: SplitterConfig
