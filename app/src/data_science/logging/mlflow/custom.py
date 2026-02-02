import mlflow
import plotly.graph_objects as go
from mlflow.entities import Run
from mlflow.tracking import MlflowClient

from src.data_science.definitions.configs.hyperparameter_tuning import HyperparameterTuningPipelineConfig


def custom_log_to_mlflow(
    config: HyperparameterTuningPipelineConfig,
    experiment_name: str,
    run_id: str,
    fig: go.Figure,
    tracking_uri: str,
) -> None:
    client = MlflowClient(tracking_uri=tracking_uri)
    experiments = [
        exp for name in [experiment_name] for exp in client.search_experiments(filter_string=f"name like '{name}'")
    ]
    assert len(experiments) == 1, f"Expected 1 experiment, got {len(experiments)}"

    run: Run = next(
        run_info
        for run_info in client.search_runs(
            experiment_ids=[exp.experiment_id for exp in experiments],
            filter_string=f"run_id = '{run_id}'",
        )
    )

    client.log_figure(run.info.run_id, fig, "validation_test_forecasts.html")
    with mlflow.start_run(run_id=run.info.run_id):
        mlflow.log_params(config.model_dump())
