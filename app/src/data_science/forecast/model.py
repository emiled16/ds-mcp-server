from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from mlflow.pyfunc.model import PythonModel
from sklearn.base import RegressorMixin

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.definitions.orchestration.pipeline import Pipeline
from src.data_science.regression.models.base import SklearnRegressorWrapper


class TimeSeriesForecastingModelWithFeatureSelection(PythonModel):
    def __init__(
        self,
        model: RegressorMixin | SklearnRegressorWrapper,
        selected_features: list[str],
        date_column: str,
        dimensions: list[str],
        metrics_name: str,
        pipeline: Pipeline | None = None,
        clip_to_zero: bool = True,
    ):
        self.pipeline = pipeline
        self.model = model
        self.selected_features = selected_features
        self.date_column = date_column
        self.dimensions = dimensions
        self.metrics_name = metrics_name
        self._init_cols()
        self.clip_to_zero = clip_to_zero

    def set_pipeline(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline

    def _init_cols(self) -> None:
        self.input_cols = self.selected_features + self.dimensions
        self.output_cols = [self.metrics_name]

    def save_artifacts(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path / "pipeline.pkl")
        joblib.dump(self.model, path / "model.pkl")

        metadata = {
            "selected_features": self.selected_features,
            "date_column": self.date_column,
            "dimensions": self.dimensions,
            "metrics_name": self.metrics_name,
        }

        joblib.dump(metadata, path / "metadata.pkl")

    def load_context(self, context: Any) -> None:
        pipeline_path = context.artifacts.get("pipeline", None)
        if pipeline_path:
            self.pipeline = joblib.load(pipeline_path)

        model_path = context.artifacts.get("model", None)
        if model_path:
            self.model = joblib.load(model_path)

        metadata_path = context.artifacts.get("metadata", None)
        if metadata_path:
            metadata = joblib.load(metadata_path)
            self.selected_features = metadata["selected_features"]
            self.date_column = metadata["date_column"]
            self.dimensions = metadata["dimensions"]
            self._init_cols()

    def fit(
        self,
        dataset: pd.DataFrame,
        first_date_to_predict: str | None = None,
        last_date_to_predict: str | None = None,
    ) -> None:
        if self.pipeline:
            pipeline_inputs = self.pipeline.get_inputs()
            input_arg = "df" if len(pipeline_inputs) == 0 else pipeline_inputs[0]

            data: pd.DataFrame = self.pipeline.fit_transform(
                **{
                    input_arg: dataset,
                    "in_memory": True,
                },
            )
        else:
            data = dataset

        data = self.select_dates(data, self.date_column, first_date_to_predict, last_date_to_predict)
        self.model.fit(data)

    def predict(self, context: Any, model_input: pd.DataFrame, params: Any = None) -> pd.DataFrame:
        if isinstance(params, dict):
            first_date_to_predict = params.get("first_date_to_predict", None)
            last_date_to_predict = params.get("last_date_to_predict", None)
        else:
            first_date_to_predict = None
            last_date_to_predict = None

        if self.pipeline:
            pipeline_inputs = self.pipeline.get_inputs()
            input_arg = "df" if len(pipeline_inputs) == 0 else pipeline_inputs[0]

            data: pd.DataFrame = self.pipeline.transform(
                **{
                    input_arg: model_input,
                    "in_memory": True,
                },
            )
        else:
            data = model_input

        data = self.select_dates(data, self.date_column, first_date_to_predict, last_date_to_predict)
        preds = self.model.predict(data)
        if self.clip_to_zero:
            preds["predictions"] = preds["predictions"].apply(lambda x: max(x, 0))
        return preds

    @staticmethod
    def select_columns(data: pd.DataFrame | SnowparkDataFrame, columns: list[str]) -> pd.DataFrame:
        return data[columns]

    @staticmethod
    def select_dates(
        data: pd.DataFrame,
        date_column: str,
        first_date_to_predict: str | None = None,
        last_date_to_predict: str | None = None,
    ) -> pd.DataFrame:
        mask1 = (
            data[date_column] >= first_date_to_predict
            if first_date_to_predict
            else data[date_column] == data[date_column]
        )
        mask2 = data[date_column] <= last_date_to_predict if last_date_to_predict else True
        selector = data[mask1 & mask2].index
        return data.loc[selector]
