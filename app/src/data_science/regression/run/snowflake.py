import json
import uuid
from typing import Any, Union

import joblib
import numpy as np
import pandas as pd
from mlflow.models.signature import ModelSignature, Schema
from mlflow.types.schema import ColSpec, DataType
from snowflake import snowpark
from snowflake.snowpark.context import get_active_session

from src.data_science.regression.configs.run import RunConfig

mapping = {
    np.float64: DataType.double,
    np.int32: DataType.integer,
    np.int64: DataType.long,
    np.float32: DataType.float,
    str: DataType.string,
    bytes: DataType.binary,
    np.datetime64: DataType.datetime,
}


def launch_run_on_snowflake(
    dataset: Union[pd.DataFrame, snowpark.DataFrame],
    config: RunConfig,
    sproc_name: str = "regression_experiment",
) -> tuple[Any, ModelSignature, dict[str, float], pd.DataFrame]:
    # save table to snowflake & convert the experiment config to a dict
    tmp_name = dataset_to_tmp_snowflake(dataset)
    database_name = get_active_session().get_current_database()
    schema_name = get_active_session().get_current_schema()
    if database_name is None or schema_name is None:
        raise ValueError("Database or schema not found")

    config_dict = config.model_dump(exclude={"model": {"model_class"}})
    sample_df = dataset.head() if isinstance(dataset, pd.DataFrame) else dataset.limit(10).to_pandas()
    # launch the run on snowflake using the sproc
    query = f"""
            CALL {sproc_name}(
                {json.dumps(config_dict).replace('"', "'")},
                '{database_name}.{schema_name}.{tmp_name}'
            )
            """.strip()

    # get the run results from snowflake
    experiment_run = get_active_session().sql(query).collect()[0][0]
    drop_tmp_table(database_name, schema_name, tmp_name)

    mlflow_dict = json.loads(experiment_run)
    data = mlflow_dict["data"]
    output_stream = get_active_session().file.get_stream(mlflow_dict["SNOWFLAKE_MODEL_PATH"])
    trained_model = joblib.load(output_stream)
    signature = ModelSignature(
        inputs=Schema(
            [ColSpec(name=col, type=mapping[np.dtype(sample_df[col]).type]) for col in trained_model.input_cols],
        ),
        outputs=Schema(
            [ColSpec(name=col, type=DataType.double) for col in trained_model.output_cols],
        ),
    )
    predictions_table_name = mlflow_dict["pred_table_tmp_name"]
    predictions_table_name = f"{database_name}.{schema_name}.{predictions_table_name}"
    predictions_df = get_active_session().table(predictions_table_name).to_pandas()

    return trained_model, signature, data.get("metrics", {}), predictions_df


def dataset_to_tmp_snowflake(dataset: Union[pd.DataFrame, snowpark.DataFrame]) -> str:
    if isinstance(dataset, pd.DataFrame):
        tmp_name = f"tmp_dataset_{uuid.uuid4()}".replace("-", "_")
        dataset = get_active_session().create_dataframe(dataset)
    dataset.write.save_as_table(tmp_name)
    return tmp_name


def drop_tmp_table(database_name: str, schema_name: str, dataset_name: str) -> None:
    get_active_session().sql(f"DROP TABLE IF EXISTS {database_name}.{schema_name}.{dataset_name}").collect()
