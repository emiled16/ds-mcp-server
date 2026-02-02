# https://www.mlflow.org/docs/latest/model-registry.html#concepts
from typing import Optional

import mlflow
import mlflow.pyfunc


def update_tag_model(model_name: str, tag_name: str, tag_value: Optional[str] = None) -> None:
    """
    Update a tag for a registered model.
    If the tag value is None, the tag is deleted.
    """
    client = mlflow.MlflowClient()
    if tag_value is None:
        client.delete_registered_model_tag(model_name, tag_name)
    else:
        client.set_registered_model_tag(model_name, tag_name, tag_value)


def update_tag_model_version(model_name: str, version: int, tag_name: str, tag_value: Optional[str] = None) -> None:
    client = mlflow.MlflowClient()
    if tag_value is None:
        client.delete_model_version_tag(model_name, str(version), tag_name)
    else:
        client.set_model_version_tag(model_name, str(version), tag_name, tag_value)


def alias_model(model_name: str, alias_name: str, version: int) -> None:
    client = mlflow.MlflowClient()
    client.set_registered_model_alias(model_name, alias_name, str(version))


def get_latest_version(model_name: str) -> int:
    client = mlflow.MlflowClient()
    return client.get_latest_versions(model_name)[0].version


def get_model_version_by_alias(model_name: str, alias_name: str) -> int:
    client = mlflow.MlflowClient()
    return client.get_model_version_by_alias(model_name, alias_name).version


def delete_model_version(model_name: str, version: int) -> None:
    client = mlflow.MlflowClient()
    client.delete_model_version(model_name, str(version))


def delete_model_version_by_alias(model_name: str, alias_name: str) -> None:
    client = mlflow.MlflowClient()
    client.delete_model_version(model_name, str(get_model_version_by_alias(model_name, alias_name)))


def delete_registered_model(model_name: str) -> None:
    client = mlflow.MlflowClient()
    client.delete_registered_model(model_name)


# fetch models:
def fetch_model_by_alias(model_name: str, alias_name: str) -> mlflow.pyfunc.PyFuncModel:
    return mlflow.pyfunc.load_model(f"models:/{model_name}@{alias_name}")


def fetch_model_by_version(model_name: str, version: int) -> mlflow.pyfunc.PyFuncModel:
    return mlflow.pyfunc.load_model(f"models:/{model_name}/{version}")
