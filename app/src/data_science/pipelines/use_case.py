from loguru import logger

from src.data_science.database.client import DBClient
from src.data_science.database.models.dim_use_cases import DimUseCases
from src.data_science.definitions.configs.use_case import UseCasePipelineConfig


def create_use_case(config: UseCasePipelineConfig, db_client: DBClient, use_case_id: str | None = None) -> str:
    if use_case_id:
        config.use_case_id = use_case_id
    use_case_id = config.use_case_id
    use_case_name = config.name

    if use_case_id:
        existing_use_case = db_client.fetch_records(
            DimUseCases,
            {"use_case_id": use_case_id},
        )
        if len(existing_use_case) > 0:
            logger.warning(f"Use case with ID {use_case_id} already exists. Skipping creation.")
            return use_case_id

    logger.info(f"Creating use case: {use_case_id} - {use_case_name}")
    db_client.insert_records(DimUseCases, [config.model_dump()])
    logger.info(f"Use case created: {use_case_id} - {use_case_name}")
    return use_case_id
