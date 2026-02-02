from pydantic import BaseModel

from src.data_science.definitions.storage import StorageConfig


class ExperimentPipelineDataConfig(BaseModel):
    training_data: StorageConfig


class FeaturePipelineDataConfig(BaseModel):
    dim_use_cases: StorageConfig
    dim_experiments: StorageConfig
    raw_data: StorageConfig
    feature_store_output: StorageConfig


class HyperparameterTuningPipelineDataConfig(BaseModel):
    training_input: StorageConfig
    dim_use_cases: StorageConfig
    dim_experiments: StorageConfig
    dim_runs: StorageConfig
    feature_store_output: StorageConfig
    training_forecast_output: StorageConfig
    training_forecast_score_output: StorageConfig


class ModelSelectionPipelineDataConfig(BaseModel):
    dim_experiments: StorageConfig
    dim_use_cases: StorageConfig
    dim_runs: StorageConfig
    training_forecast_output: StorageConfig
    training_forecast_score_output: StorageConfig
    model_selection_output: StorageConfig


class InferencePipelineDataConfig(BaseModel):
    inference_input: StorageConfig
