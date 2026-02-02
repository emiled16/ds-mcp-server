import pandas as pd

from src.data_science.ds_core.definitions.orchestration.pipeline import Pipeline
from src.data_science.treasury_forecasting.constants import DIMENSION_ID_COLUMN


def get_features(
    pipeline: Pipeline,
    data: pd.DataFrame,
    date_column: str,
    dimensions: list[str],
    metrics_name: str,
) -> list[str]:
    return list(
        set(pipeline.fit_transform(step1__df=data).columns)
        - {metrics_name}
        - {date_column}
        - set(dimensions or [])
        - {DIMENSION_ID_COLUMN},
    )
