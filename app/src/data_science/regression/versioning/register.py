from typing import Any

import mlflow


def register_model(
    experiment_name: str,
    run_id: str,
    model_name: str,
    tags: dict[str, Any] = {"stage": "dev"},
) -> None:
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise ValueError(f"Experiment {experiment_name} not found")
    run = client.get_run(run_id)
    model_uri = f"{run.info.artifact_uri}/model"
    mlflow.register_model(
        model_uri=model_uri,
        name=model_name,
        tags=tags,
    )
