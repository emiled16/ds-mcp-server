import pandas as pd

from src.data_science.forecast.model import TimeSeriesForecastingModelWithFeatureSelection


def predict(
    model: TimeSeriesForecastingModelWithFeatureSelection,
    data: pd.DataFrame,
    first_date_to_predict: str | None = None,
    last_date_to_predict: str | None = None,
) -> pd.DataFrame:
    return model.predict(
        context=None,
        model_input=data,
        params={
            "first_date_to_predict": first_date_to_predict,
            "last_date_to_predict": last_date_to_predict,
        },
    )
