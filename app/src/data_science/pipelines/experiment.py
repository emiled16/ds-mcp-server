from loguru import logger

from src.data_science.database.client import DBClient
from src.data_science.database.models.dim_experiments import DimExperiments
from src.data_science.database.models.dim_use_cases import DimUseCases
from src.data_science.definitions.configs.experiment import ExperimentPipelineConfig


def create_experiment(
    config: ExperimentPipelineConfig,
    db_client: DBClient,
    use_case_id: str | None = None,
    experiment_id: str | None = None,
) -> str:
    if experiment_id:
        config.experiment_id = experiment_id
    if use_case_id:
        config.experiments.use_case_id = use_case_id

    experiment_id = config.experiment_id
    experiment_name = config.experiments.experiment_name
    use_case_records = db_client.fetch_records(DimUseCases, {"use_case_id": config.experiments.use_case_id})

    if len(use_case_records) == 0:
        raise ValueError(f"Use case {config.experiments.use_case_id} not found")
    if len(use_case_records) > 1:
        raise ValueError(f"Multiple use cases found for {config.experiments.use_case_id}")

    if experiment_id is None:
        raise ValueError("Experiment ID must be provided or generated")

    existing_experiment = db_client.fetch_records(
        DimExperiments,
        {"experiment_id": experiment_id},
    )
    if len(existing_experiment) > 0:
        logger.warning(f"Experiment with ID {experiment_id} already exists. Skipping creation.")
        return experiment_id

    logger.info(f"Creating experiment: {experiment_id} - {experiment_name}")

    record = {
        "experiment_id": experiment_id,
        "use_case_id": use_case_records[0]["use_case_id"],
        "name": experiment_name,
        "description": config.experiments.description,
        "config": config.model_dump(),
    }

    db_client.insert_records(DimExperiments, [record])
    logger.info(f"Experiment created: {experiment_id} - {experiment_name}")
    return experiment_id
