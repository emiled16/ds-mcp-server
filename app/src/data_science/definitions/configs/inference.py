from pydantic import BaseModel

from src.data_science.definitions.configs.components.data import InferencePipelineDataConfig


class MetadataConfig(BaseModel):
    experiment_id: str
    min_date: str | None = None
    max_date: str


class InferencePipelineConfig(BaseModel):
    metadata: MetadataConfig
    data: InferencePipelineDataConfig
