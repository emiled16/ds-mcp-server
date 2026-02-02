from collections.abc import Callable
from typing import Literal

from snowflake import snowpark
from snowflake.ml.registry import Registry
from snowflake.snowpark.types import DataType


def inference_sp(
    session: snowpark.Session,
    input_table_name: str,
    model_name: str,
    model_version: str,
    output_table_name: str,
    mode: Literal["overwrite", "append"] = "overwrite",
) -> str:
    reg = Registry(session=session)
    m = reg.get_model(model_name)  # Fetch the model using the registry
    mv = m.version(model_version)

    df = session.table(input_table_name)
    results = mv.run(df, function_name="predict")  # 'results' is the output DataFrame with predictions

    results.write.save_as_table(output_table_name, mode=mode)

    return "Success"


def register_inference_sproc(
    session: snowpark.Session,
    sproc_name: str,
    sproc_func: Callable,
    packages: list[str],
    return_type: DataType,
    stage_location: str,
):
    # Register the stored procedure
    session.sproc.register(
        func=sproc_func,
        name=sproc_name,
        replace=True,
        is_permanent=True,
        stage_location=stage_location,
        packages=packages,
        return_type=return_type,
    )
