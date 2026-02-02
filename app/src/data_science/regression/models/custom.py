from pathlib import Path

import joblib
import pandas as pd
from mlflow.pyfunc.model import PythonModel

from src.data_science.ds_core.definitions.orchestration.pipeline import Pipeline
from src.data_science.regression.models.base import SnowflakeModelClassType


class CustomModel(PythonModel):
    def __init__(self, pipeline: Pipeline, model: SnowflakeModelClassType):
        self.pipeline = pipeline
        self.model = model

    def save_artifacts(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path / "pipeline.pkl")
        joblib.dump(self.model, path / "model.pkl")

    def load_context(self, context):
        pipeline_path = context.artifacts.get("pipeline", None)
        if pipeline_path:
            self.pipeline = joblib.load(pipeline_path)

        model_path = context.artifacts.get("model", None)
        if model_path:
            self.model = joblib.load(model_path)

    def fit(self, dataset: pd.DataFrame):
        # TODO: modify how to handel input of pipeline
        pipeline_inputs = self.pipeline.get_inputs()
        input_arg = "df" if len(pipeline_inputs) == 0 else pipeline_inputs[0]
        data = self.pipeline.fit_transform(
            **{
                input_arg: dataset,
                "in_memory": True,
            }
        )
        self.model.fit(data)

    def predict(self, context, model_input, params=None) -> pd.DataFrame:
        pipeline_inputs = self.pipeline.get_inputs()
        input_arg = "df" if len(pipeline_inputs) == 0 else pipeline_inputs[0]
        data = self.pipeline.transform(
            **{
                input_arg: model_input,
                "in_memory": True,
            }
        )
        return self.model.predict(data)
