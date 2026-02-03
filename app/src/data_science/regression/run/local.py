from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from mlflow.models.signature import ModelSignature, Schema
from mlflow.types.schema import ColSpec, DataType

from src.data_science.ds_core.definitions.splitters import Splitter
from src.data_science.ds_core.definitions.splitters.enum import Split
from src.data_science.regression.metrics import Scorer
from src.data_science.regression.models.custom import CustomModel
from src.data_science.snowflake_optional import SNOWFLAKE_AVAILABLE, SnowparkDataFrame

mapping = {
    np.float64: DataType.double,
    np.int32: DataType.integer,
    np.int64: DataType.long,
    np.float32: DataType.float,
    str: DataType.string,
    bytes: DataType.binary,
    np.datetime64: DataType.datetime,
    np.bool_: DataType.boolean,
    bool: DataType.boolean,
    np.uint32: DataType.long,
}


def launch_run_locally(
    dataset: pd.DataFrame | Any,
    python_model: CustomModel,
    splitter: Splitter,
    scorer: Scorer,
    target_cols: list[str],
    output_cols: list[str],
    input_cols: list[str],
    logger_context: str,
) -> tuple[Any, ModelSignature, dict[str, float], pd.DataFrame]:
    dataset = (
        dataset.to_pandas()
        if (SNOWFLAKE_AVAILABLE and SnowparkDataFrame is not None and isinstance(dataset, SnowparkDataFrame))
        else dataset
    )

    all_predictions = []
    fold_scores = {}
    for fold_idx, (train_clause, test_clause) in enumerate(splitter.split(dataset)):
        logger.debug(f"{logger_context} - Fold {fold_idx}")
        train_dataset = dataset.loc[dataset.index.isin(train_clause)]
        test_dataset = dataset.loc[dataset.index.isin(test_clause)]

        python_model.fit(dataset=train_dataset)

        # Get train predictions
        train_predictions = python_model.predict(
            context=None,
            model_input=train_dataset,
        )
        train_predictions["split"] = Split.TRAIN.value
        train_predictions["fold"] = fold_idx
        train_scores = scorer.evaluate(
            train_predictions,
            y_pred_col_names=output_cols,
            y_true_col_names=target_cols,
        )

        # Get test predictions
        validation_predictions = python_model.predict(
            context=None,
            model_input=test_dataset,
        )
        validation_predictions["split"] = Split.VALIDATION.value
        validation_predictions["fold"] = fold_idx
        validation_scores = scorer.evaluate(
            validation_predictions,
            y_pred_col_names=output_cols,
            y_true_col_names=target_cols,
        )

        # Store fold-specific scores
        fold_scores[fold_idx] = {
            Split.TRAIN.value: train_scores,
            Split.VALIDATION.value: validation_scores,
        }

        all_predictions.append(pd.concat([train_predictions, validation_predictions]))

    logger.debug(f"{logger_context} - Dataset Fit")
    python_model.fit(dataset=dataset)

    predictions = pd.concat(all_predictions)

    model_signature = ModelSignature(
        inputs=Schema(
            [ColSpec(name=col, type=mapping[predictions[col].dtype.type]) for col in input_cols],
        ),
        outputs=Schema(
            [ColSpec(name=col, type=DataType.double) for col in output_cols],
        ),
    )

    return python_model, model_signature, fold_scores, predictions


def flatten_scores(scores: dict[str, dict[str, dict[str, float]]]) -> dict[str, float]:
    return {
        f"{metric_name}__{split}__{fold}": metric_value
        for fold, folds in scores.items()
        for split, metrics in folds.items()
        for metric_name, metric_value in metrics.items()
    }


def summarize_scores(
    scores: dict[str, dict[str, dict[str, float]]],
) -> dict[str, float]:
    folds = list(scores.keys())
    splits = list(scores[folds[0]].keys())
    metrics = list(scores[folds[0]][splits[0]].keys())

    aggregated_scores = {}
    for split in splits:
        for metric in metrics:
            aggregated_scores[f"{metric}__{split}"] = np.mean(
                [scores.get(fold, {}).get(split, {}).get(metric, None) for fold in folds],
            )

    return aggregated_scores
