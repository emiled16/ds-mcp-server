from typing import Any, Union

import pandas as pd
from mlflow.models.signature import ModelSignature
from snowflake import snowpark

from src.data_science.ds_core.definitions.splitters import Splitter
from src.data_science.regression.configs.run import RunConfig
from src.data_science.regression.metrics import Scorer
from src.data_science.regression.models.custom import CustomModel
from src.data_science.regression.run.local import launch_run_locally
from src.data_science.regression.run.logger import log_run


def launch_run(
    dataset: Union[pd.DataFrame, snowpark.DataFrame],
    python_model: CustomModel,
    splitter: Splitter,
    scorer: Scorer,
    target_cols: list[str],
    output_cols: list[str],
    input_cols: list[str],
    config: RunConfig,
    trial_number: int,
    on_snowflake: bool = False,
) -> tuple[Any, ModelSignature, dict[str, float], pd.DataFrame, str]:
    # run_experiment = launch_run_on_snowflake if on_snowflake else launch_run_locally

    # run_logged_experiment = log_run(run_experiment)

    run_logged_experiment = log_run(launch_run_locally)

    trained_model, model_signature, scores, predictions, run_id, raw_scores = run_logged_experiment(
        dataset=dataset,
        python_model=python_model,
        splitter=splitter,
        scorer=scorer,
        target_cols=target_cols,
        output_cols=output_cols,
        input_cols=input_cols,
        config=config,
        trial_number=trial_number,
        is_running_in_sproc=on_snowflake,
    )

    return trained_model, model_signature, scores, predictions, run_id, raw_scores
