import re
from typing import Optional, get_args

from src.data_science.regression.metrics import Metric


def get_list_of_metrics() -> list[type]:
    if not hasattr(Metric, "__origin__"):
        raise ValueError("RegressorModel is not a valid model")

    all_metrics = get_args(Metric.__origin__)
    return list(all_metrics)


def parse_metric_name(metric_name: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", metric_name)


def get_metrics_name() -> list[str]:
    all_metrics = get_list_of_metrics()
    return [parse_metric_name(metric.__name__) for metric in all_metrics]


def get_metric_class(metric_name: Optional[str]) -> Optional[type]:
    if metric_name is None:
        return None
    all_metrics = get_list_of_metrics()
    return next((metric for metric in all_metrics if parse_metric_name(metric.__name__) == metric_name), None)
