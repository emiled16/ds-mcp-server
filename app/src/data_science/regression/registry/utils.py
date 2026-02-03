import glob
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import mlflow
from mlflow.pyfunc import PyFuncModel
from mlflow.tracking.artifact_utils import _download_artifact_from_uri

from src.data_science.regression.models.custom import CustomModel
from src.data_science.snowflake_optional import ModelSignature, Registry, Session, require_snowflake


def process_mlflow_types(data):
    # Iterate over each key in the dictionary
    for key in data:
        # Iterate over each item in the list associated with the key
        for item in data[key]:
            # Check if the type is 'double' and change it to 'float'
            item["type"] = item["type"].upper()
    return data


def process_model_signature(model_conf: PyFuncModel) -> ModelSignature:
    require_snowflake()
    return ModelSignature.from_dict(
        process_mlflow_types({k: json.loads(v) for k, v in model_conf.metadata.signature.to_dict().items() if v}),
    )


def get_model_path_from_mlflow(
    experiment_name: str,
    run_id: str,
    artifact_model_name: str = "model",
) -> str:
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise ValueError(f"Experiment {experiment_name} not found")
    run = client.get_run(run_id)
    model_uri = f"{run.info.artifact_uri}/{artifact_model_name}"
    return _download_artifact_from_uri(model_uri)


def get_metrics(
    experiment_name: str,
    run_id: str,
) -> dict[str, Any]:
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise ValueError(f"Experiment {experiment_name} not found")
    run = client.get_run(run_id)
    return run.data.metrics


def get_model_data_from_mlflow(
    experiment_name: str,
    run_id: str,
    artifact_model_name: str = "model",
) -> tuple[CustomModel, dict[str, Any], str, ModelSignature]:
    model_path = get_model_path_from_mlflow(experiment_name, run_id, artifact_model_name)
    metrics = get_metrics(experiment_name, run_id)

    model_conf = mlflow.pyfunc.load_model(model_path)
    model = model_conf.unwrap_python_model()
    model_signature = process_model_signature(model_conf)
    return model, metrics, model_path, model_signature


def get_model_registry(
    session: Session,
    database_name: str,
    schema_name: str,
) -> Registry:
    return Registry(session=session, database_name=database_name, schema_name=schema_name)


def bundle_model_files(tmpdir: Path, lib_prefix: str = "maxa") -> None:
    paths = [
        Path(__file__).parent.parent.parent.parent,
        Path(__file__).parent.parent.parent.parent.parent / "core",
    ]
    (tmpdir / lib_prefix).mkdir(parents=True, exist_ok=True)

    for path in paths:
        file_path = f"{path!s}/**/*.py"
        for file in glob.glob(file_path, recursive=True):
            relative_path = file.split(f"/{lib_prefix}/")
            # create the directories:
            folders = relative_path[-1].split("/")
            root = tmpdir / lib_prefix
            for folder in folders:
                if ".py" not in folder:
                    root = root / folder
                    root.mkdir(parents=True, exist_ok=True)
                else:
                    shutil.copy(file, root)


def register_model_to_snowflake(
    model_path: str,
    model_name: str,
    version_name: str,
    model_registry: Registry,
    metrics: dict[str, Any] | None = None,
    comment: str | None = None,
    python_version: str | None = "3.10",
    embed_local_ml_library: bool = True,
    conda_dependencies: list[str] = [
        "pydantic",
        "mlflow",
        "loguru",
        "plotly",
        "networkx",
        "python-dotenv",
        "optuna",
        "streamlit",
    ],
):
    require_snowflake()
    with tempfile.TemporaryDirectory() as tmpdir:
        LIB_PREFIX = "maxa"
        bundle_model_files(Path(tmpdir), LIB_PREFIX)
        model_registry.log_model(
            mlflow.pyfunc.load_model(model_path),
            model_name=model_name,
            version_name=version_name,
            conda_dependencies=conda_dependencies,
            code_paths=[str(model_path), str(Path(tmpdir) / LIB_PREFIX)],
            metrics=metrics,
            options={
                "embed_local_ml_library": embed_local_ml_library,
            },
            python_version=python_version,
            comment=comment,
        )
