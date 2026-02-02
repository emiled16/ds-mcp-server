from snowflake.snowpark import Session

from src.data_science.data_engine_db_client import DataEngineDbClientBuilder
from src.data_science.data_engine_db_client.data_engine_db_client import DataEngineDbClientInterface
from src.data_science.data_engine_db_client.snowflake import new_snowflake_cloud_provider_infos
from src.data_science.snowflake.native_app_events import setup_native_app_events
from src.data_science.snowflake.native_app_logger import init_native_app_logger
from src.data_science.treasury_forecasting.constants import STAGE_PATH


def init_db_client(
    session: Session,
    name: str,
    files_stage: str = STAGE_PATH,
) -> DataEngineDbClientInterface:
    setup_native_app_events(session=session, source=name)
    init_native_app_logger(
        app_name=name,
        session=session,
    )

    return (
        DataEngineDbClientBuilder()
        .with_cloud_provider_infos(
            new_snowflake_cloud_provider_infos(
                session=session,
                files_stage=files_stage,
            ),
        )
        .build()
    )
