import pandas as pd
import plotly.graph_objects as go

from src.data_science.ds_core.definitions.splitters.enum import Split
from src.data_science.forecast.model import TimeSeriesForecastingModelWithFeatureSelection
from src.data_science.forecast.predict import predict
from src.data_science.regression.metrics import Scorer
from src.data_science.visualizations.predictions import plot_predictions


def get_final_output(
    predictions: pd.DataFrame,
    split_column: str = "split",
    date_column: str = "date",
    fold_column: str = "fold",
) -> pd.DataFrame:
    indexes = predictions.index.names
    test_predictions = predictions[predictions[split_column] == Split.TEST.value]

    validation_predictions = predictions[predictions[split_column] == Split.VALIDATION.value]

    # test_predictions = predictions.query(f"split == '{Split.TEST.value}'")
    validation_predictions = (
        predictions.query(f"{split_column} == '{Split.VALIDATION.value}'")
        .groupby(indexes)
        .apply(lambda x: x.sort_values(by=fold_column).iloc[-1])
    )

    return pd.concat([test_predictions, validation_predictions]).sort_values(by=date_column)


def postprocess_predictions(
    model: TimeSeriesForecastingModelWithFeatureSelection,
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    predictions: pd.DataFrame,
    date_column: str,
    forecasting_target_cols: list[str],
    forecasting_output_cols: list[str],
    prediction_column: str,
    scorer: Scorer,
) -> tuple[pd.DataFrame, dict[str, float], go.Figure]:
    test_min_date = test_data[date_column].min()
    test_max_date = test_data[date_column].max()

    test_predictions = predict(
        model=model,
        data=pd.concat([train_data, test_data]),
        first_date_to_predict=test_min_date,
        last_date_to_predict=test_max_date,
    ).assign(
        split=Split.TEST.value,
        fold=None,
    )
    test_scores = scorer.evaluate(
        dataset=test_predictions,
        y_true_col_names=forecasting_target_cols,
        y_pred_col_names=forecasting_output_cols,
    )

    plotting_predictions = get_final_output(
        pd.concat([predictions, test_predictions]),
        date_column=date_column,
        split_column="split",
        fold_column="fold",
    )

    fig = plot_predictions(
        predictions=plotting_predictions,
        actual_column=forecasting_target_cols[0],
        prediction_column=prediction_column,
        date_column=date_column,
        split_column="split",
    )
    return test_predictions, test_scores, fig
