import argparse
from pathlib import Path

# It's often safer to use a more generic type like argparse.Action
# or even Any if _SubParsersAction causes issues with some linters/versions.
# For now, let's try with the specific internal type if your environment handles it.
SubParsersAction = argparse._SubParsersAction  # type: ignore


def add_use_case_parser(subparsers: SubParsersAction) -> None:
    parser = subparsers.add_parser("use_case")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--use_case_id", type=str, required=False, default=None)


def add_experiment_parser(subparsers: SubParsersAction) -> None:
    parser = subparsers.add_parser("experiment")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--use_case_id", type=str, required=False, default=None)
    parser.add_argument("--experiment_id", type=str, required=False, default=None)


def add_feature_store_parser(subparsers: SubParsersAction) -> None:
    parser = subparsers.add_parser("feature_store")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--experiment_id", type=str, required=False, default=None)
    parser.add_argument("--feature_store_id", type=str, required=False, default=None)


def add_hyperparameter_tuning_parser(subparsers: SubParsersAction) -> None:
    parser = subparsers.add_parser("hyperparameter_tuning")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runs_number", type=int, required=False, default=1)
    parser.add_argument("--holdout_splitter", type=float, required=False, default=0.2)
    parser.add_argument("--last_test_date", type=str, required=False, default=None)
    parser.add_argument("--feature_store_id", type=str, required=False, default=None)


def add_model_selection_parser(subparsers: SubParsersAction) -> None:
    parser = subparsers.add_parser("model_selection")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--metric", type=str, required=False, default=None)
    parser.add_argument("--last_test_date", type=str, required=False, default=None)
    parser.add_argument("--experiment_id", type=str, required=False, default=None)
    parser.add_argument("--feature_store_id", type=str, required=False, default=None)


def add_inference_parser(subparsers: SubParsersAction) -> None:
    parser = subparsers.add_parser("inference")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--experiment_id", type=str, required=False, default=None)
    parser.add_argument("--test_date", type=str, required=False, default=None)
    parser.add_argument("--run_id", type=str, required=False, default=None)


def define_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    add_use_case_parser(subparsers)
    add_experiment_parser(subparsers)
    add_feature_store_parser(subparsers)
    add_hyperparameter_tuning_parser(subparsers)
    add_model_selection_parser(subparsers)
    add_inference_parser(subparsers)
    return parser
