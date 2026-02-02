from typing import Optional

from loguru import logger
from snowflake.snowpark.context import get_active_session


def init_monitoring(
    monitoring_pipeline_name: str,
    model_name: str,
    version: str,
    source: str,
    baseline: str,
    timestamp_column: str,
    prediction_class_columns: list[str],
    actual_class_columns: list[str],
    id_columns: list[str],
    warehouse: str,
    database_name: Optional[str] = None,
    schema_name: Optional[str] = None,
    function: str = "predict",
    refresh_interval: str = "1 min",
    aggregation_window: str = "1 day",
):
    if database_name is not None:
        get_active_session().use_database(database_name)
    if schema_name is not None:
        get_active_session().use_schema(schema_name)
    query = f"""
    CREATE OR REPLACE MODEL MONITOR {monitoring_pipeline_name}
    WITH
        MODEL={model_name}
        VERSION={version}
        FUNCTION={function}
        SOURCE={source}
        BASELINE={baseline}
        TIMESTAMP_COLUMN={timestamp_column}
        PREDICTION_CLASS_COLUMNS={prediction_class_columns}  
        ACTUAL_CLASS_COLUMNS={actual_class_columns}
        ID_COLUMNS={id_columns}
        WAREHOUSE={warehouse}
        REFRESH_INTERVAL={refresh_interval}
        AGGREGATION_WINDOW={aggregation_window};
    """
    try:
        get_active_session().sql(query).collect()
        logger.info(f"Monitoring pipeline {monitoring_pipeline_name} created successfully")
    except Exception as e:
        logger.error(f"Error creating monitoring pipeline: {e}")
        raise e


def delete_monitoring(monitoring_pipeline_name: str):
    query = f"DROP MODEL MONITOR {monitoring_pipeline_name};"
    get_active_session().sql(query).collect()
    logger.info(f"Monitoring pipeline {monitoring_pipeline_name} deleted successfully")
