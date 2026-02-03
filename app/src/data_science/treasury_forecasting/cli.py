from src.data_science.utils.setup import setup_environment

setup_environment()
import os
import random

import numpy as np
import yaml
from dotenv import load_dotenv

from src.data_science.database.client import DBClient
from src.data_science.database.engine import get_engine
from src.data_science.definitions.configs.experiment import ExperimentPipelineConfig
from src.data_science.definitions.configs.feature_store import FeaturePipelineConfig
from src.data_science.definitions.configs.hyperparameter_tuning import HyperparameterTuningPipelineConfig
from src.data_science.definitions.configs.inference import InferencePipelineConfig
from src.data_science.definitions.configs.model_selection import ModelSelectionPipelineConfig
from src.data_science.definitions.configs.use_case import UseCasePipelineConfig
from src.data_science.pipelines.experiment import create_experiment
from src.data_science.pipelines.feature_store import feature_store
from src.data_science.pipelines.hyperparameter_tuning import hyperparameter_tuning
from src.data_science.pipelines.inference import inference
from src.data_science.pipelines.model_selection import model_selection
from src.data_science.pipelines.use_case import create_use_case
from src.data_science.treasury_forecasting.constants import SEED
from src.data_science.utils.parser import define_parser

random.seed(SEED)
np.random.seed(SEED)


def main() -> None:
    load_dotenv(".env", override=True)
    parser = define_parser()
    args = parser.parse_args()

    engine = get_engine()
    file_storage_path = os.getenv("FILE_STORAGE_PATH")
    db_client = DBClient(engine, file_storage_path=file_storage_path)

    match args.command:
        case "use_case":
            create_use_case(
                UseCasePipelineConfig.model_validate(yaml.safe_load(args.config.read_text()).get("use_case")),
                db_client,
                args.use_case_id,
            )
        case "experiment":
            create_experiment(
                ExperimentPipelineConfig.model_validate(yaml.safe_load(args.config.read_text())),
                db_client,
                args.use_case_id,
                args.experiment_id,
            )
        case "feature_store":
            feature_store(
                FeaturePipelineConfig.model_validate(yaml.safe_load(args.config.read_text())),
                db_client,
                args.experiment_id,
                args.feature_store_id,
            )
        case "hyperparameter_tuning":
            hyperparameter_tuning(
                HyperparameterTuningPipelineConfig.model_validate(yaml.safe_load(args.config.read_text())),
                db_client,
                args.feature_store_id,
            )
        case "model_selection":
            model_selection(
                ModelSelectionPipelineConfig.model_validate(
                    yaml.safe_load(args.config.read_text()).get("model_selection"),
                ),
                db_client,
                args.experiment_id,
                args.feature_store_id,
            )
        case "inference":
            inference(
                InferencePipelineConfig.model_validate(yaml.safe_load(args.config.read_text())),
                db_client,
                args.experiment_id,
                args.run_id,
                args.test_date,
            )
        case _:
            raise ValueError(f"Command {args.command} not found")


if __name__ == "__main__":
    main()
