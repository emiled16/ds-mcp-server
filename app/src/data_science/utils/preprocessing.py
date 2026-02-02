import json

import pandas as pd

from src.data_science.definitions.configs.components.timeseries import Periodicity
from src.data_science.treasury_forecasting.constants import DIMENSION_ID_COLUMN


def to_period(data: pd.DataFrame, date_column: str, periodicity: Periodicity) -> pd.DataFrame:
    match periodicity:
        case "daily":
            return data.assign(
                **{
                    date_column: lambda df: df[date_column].dt.to_period("D").dt.start_time,
                },
            )
        case "weekly":
            return data.assign(
                **{
                    date_column: lambda df: df[date_column].dt.to_period("W").dt.start_time,
                },
            )
        case "monthly":
            return data.assign(
                **{
                    date_column: lambda df: df[date_column].dt.to_period("M").dt.start_time,
                },
            )
        case "quarterly":
            return data.assign(
                **{
                    date_column: lambda df: df[date_column].dt.to_period("Q").dt.start_time,
                },
            )
        case "yearly":
            return data.assign(
                **{
                    date_column: lambda df: df[date_column].dt.to_period("Y").dt.start_time,
                },
            )


def prepare_timeseries(
    data: pd.DataFrame,
    date_column: str,
    dimensions: list[str],
    metrics_name: str,
    aggregation_method: str,
    aggregated_metrics_name: str,
    periodicity: Periodicity,
) -> pd.DataFrame:
    if pd.api.types.is_period_dtype(data[date_column]):
        data[date_column] = data[date_column].dt.to_timestamp()
    else:
        data[date_column] = pd.to_datetime(data[date_column])

    data = data.pipe(to_period, date_column, periodicity)

    data = data.set_index([date_column, *dimensions])
    data = data.groupby([date_column, *dimensions]).agg(
        **{aggregated_metrics_name: (metrics_name, aggregation_method)},
    )
    data = data.reset_index().assign(
        **{f"{col}_idx": lambda df, col=col: df[col] for col in [*dimensions, date_column]},
    )
    data = data.set_index([f"{col}_idx" for col in [*dimensions, date_column]])

    data[DIMENSION_ID_COLUMN] = data[dimensions].apply(
        lambda x: json.dumps(x.to_dict()),
        axis=1,
    )

    return data
