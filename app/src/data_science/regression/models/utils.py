import re
from typing import Optional, get_args

from src.data_science.regression.models import RegressorGridSearchConfig, RegressorModel


def get_list_of_models() -> list[type]:
    if not hasattr(RegressorModel, "__origin__"):
        raise ValueError("RegressorModel is not a valid model")

    all_models = get_args(RegressorModel.__origin__)
    return list(all_models)


def get_list_of_grid_classes() -> list[type]:
    all_models = get_args(RegressorGridSearchConfig.__origin__)
    return [model.model_class for model in all_models]


def parse_model_name(model_name: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", model_name.split("Regressor")[0])


def parse_grid_name(grid_name: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", grid_name.split("GridSearch")[0])


def get_model_class(model_name: Optional[str]) -> Optional[type]:
    if model_name is None:
        return None
    all_models = get_list_of_models()
    return next((model for model in all_models if parse_model_name(model.__name__) == model_name), None)


def get_model_names() -> list[str]:
    all_models = get_list_of_models()
    return [parse_model_name(model.__name__) for model in all_models]


def get_grid_class_from_model_name(model_name: str) -> Optional[type]:
    all_grid_classes = get_list_of_grid_classes()
    return next(
        (grid_class for grid_class in all_grid_classes if parse_grid_name(grid_class.__name__) == model_name),
        None,
    )
