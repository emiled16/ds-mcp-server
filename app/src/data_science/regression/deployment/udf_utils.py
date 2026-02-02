import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import yaml
from loguru import logger
from mlflow.exceptions import MlflowException
from mlflow.models import Model
from mlflow.pyfunc import FLAVOR_NAME as PYFUNC_FLAVOR_NAME
from snowflake.snowpark import Session
from snowflake.snowpark.types import (
    BooleanType,
    ByteType,
    FloatType,
    IntegerType,
    PandasDataFrameType,
    PandasSeriesType,
    StringType,
)

from src.data_science.regression.deployment.pkg_utils import extract_package_requirements

_MLMODEL_FILE_NAME = "MLmodel"
_REQUIREMENTS_TXT = "requirements.txt"
_DTYPE_TYPE_MAPPING = {
    np.dtype("float64"): FloatType(),
    np.dtype("float32"): FloatType(),
    np.dtype("int64"): IntegerType(),
    np.dtype("bool"): BooleanType(),
    np.dtype("int32"): IntegerType(),
    np.dtype("str"): StringType(),
    np.dtype("bytes"): ByteType(),
}

# `model_dir_name` is the directory name of the model
# `col_statement` is used to assign dataframe columns
# `max_batch_size_string` is the max batch size
# `test_statements` used for model deploy regression test before start of inference
_UDF_CODE_TEMPLATE = """
import pandas as pd
import sys
import os
from filelock import FileLock
import threading
import zipfile
import mlflow
import uuid
import tempfile
from _snowflake import vectorized


IMPORT_DIRECTORY_NAME = "snowflake_import_directory"
import_dir = sys._xoptions[IMPORT_DIRECTORY_NAME]
model_dir_name = '{model_dir_name}'
zip_model_path = os.path.join(import_dir, '{model_dir_name}.zip')
# only tmp is writable.
extracted = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
extracted_model_dir_path = os.path.join(extracted, model_dir_name)

with FileLock(os.path.join(tempfile.gettempdir(), 'lockfile.LOCK')):
    if not os.path.isdir(extracted_model_dir_path):
        with zipfile.ZipFile(zip_model_path, 'r') as myzip:
            myzip.extractall(extracted)
model = mlflow.pyfunc.load_model(extracted_model_dir_path)

@vectorized(input=pd.DataFrame, max_batch_size={max_batch_size_string})
def infer(df):
    {col_statement}
    ans = model.predict(df)
    return pd.Series(ans)

{test_statements}
"""

# `serialized_dx`: JSON serialized 2d pd.DataFrame
# `serialized_dy`: JSON serialized pd.Series
_MODEL_TEST_TEMPLATE = """
_test_X=pd.read_json('{serialized_dx}')
_test_y=pd.read_json('{serialized_dy}', typ='series')
assert isinstance(_test_X, pd.DataFrame)
assert isinstance(_test_y, pd.Series)

import numpy as np

np.testing.assert_almost_equal(_test_y.to_numpy(), infer(_test_X).to_numpy())
"""


def remove_tag_from_signature(signature: dict, tag: str = "required") -> dict:
    """
    Remove a tag from the signature of the model.
    Returns a new signature with the tag removed.
    """
    new_signature = {}
    for k, v in signature.items():
        if v is not None:
            v_dict = json.loads(v)
            for item in v_dict:
                if tag in item:
                    item.pop(tag)
            new_signature[k] = json.dumps(v_dict)
        else:
            new_signature[k] = None
    return new_signature


def read_conf(model_uri: str) -> dict:
    """
    Read the configuration from the MLmodel file.
    """
    with open(f"{model_uri}/MLmodel") as f:
        return yaml.safe_load(f)


def write_conf(conf: dict, model_uri: str) -> None:
    """
    Write the configuration to the MLmodel file.
    """
    with open(f"{model_uri}/MLmodel", "w") as f:
        yaml.safe_dump(conf, f)


def remove_required_in_signature(model_uri: str) -> None:
    """
    Remove the "required" tag from the signature of the model.
    """
    conf = read_conf(model_uri=model_uri)
    conf["signature"] = remove_tag_from_signature(signature=conf["signature"], tag="required")

    write_conf(conf=conf, model_uri=model_uri)


class InferUDFHelper:
    def __init__(
        self,
        model_path: str,
        name: str,
        use_latest_package_version: bool,
        stage_location: Optional[str],
    ) -> None:
        self._model_path = model_path
        self._name = name
        model_config_path = Path(self._model_path) / _MLMODEL_FILE_NAME
        self._model_conf = Model.load(model_config_path)
        requirements_txt_path = Path(model_path) / _REQUIREMENTS_TXT
        self._pkg_requirements = _handle_package_versions(
            str(requirements_txt_path), use_latest_package_version=use_latest_package_version
        )
        self._stage_location = stage_location

    def generate_udf(
        self,
        *,
        session: Session,
        max_batch_size: Optional[int],
        persist_udf_file: bool,
        test_data_X: Optional[pd.DataFrame],
        test_data_y: Optional[pd.Series],
    ):
        """Generate model backed UDF in Snowflake warehouse.

        Args:
            session (Session): A snowpark session.
            max_batch_size (Optional[int]): User provided max_batch_size configuration.
            persist_udf_file (bool): Whether to persist generated UDF file.
            test_data_X (Optional[pd.DataFrame]): Test input data as 2d dataframe.
            test_data_y (Optional[pd.Series]): Test prediction data as series.
        """
        self._autogen_model_infer_udf(
            session,
            self._model_conf.signature,
            self._model_path,
            self._name,
            packages=self._pkg_requirements,
            stage_location=self._stage_location,
            max_batch_size=max_batch_size,
            persist_udf_file=persist_udf_file,
            test_data_X=test_data_X,
            test_data_y=test_data_y,
        )

    @staticmethod
    def _autogen_model_infer_udf(
        session: Session,
        model_signature,
        model_full_path: str,
        udf_name: str,
        packages: list[str],
        stage_location: Optional[str],
        max_batch_size: Optional[int] = None,
        persist_udf_file: bool = False,
        test_data_X: Optional[pd.DataFrame] = None,
        test_data_y: Optional[pd.Series] = None,
    ):
        output_type = model_signature.outputs.numpy_types()[0]
        input_types = model_signature.inputs.numpy_types()
        try:
            snowpark_input_types = [_DTYPE_TYPE_MAPPING[dt] for dt in input_types]
        except KeyError as key_error:
            raise MlflowException(
                "Invalid datatype encountered in input model signature. Valid types are:",
                *_DTYPE_TYPE_MAPPING.keys(),
            ) from key_error
        try:
            snowpark_output_type = _DTYPE_TYPE_MAPPING[output_type]
        except KeyError as key_error:
            raise MlflowException(
                "Invalid datatype encountered in output model signature. Valid types are:",
                *_DTYPE_TYPE_MAPPING.keys(),
            ) from key_error
        max_batch_size_string = "None" if max_batch_size is None else f"{max_batch_size}"
        test_statements = ""
        if test_data_X is not None and test_data_y is not None:
            serialized_dx = test_data_X.to_json()
            serialized_dy = test_data_y.to_json()
            test_statements = _MODEL_TEST_TEMPLATE.format(serialized_dx=serialized_dx, serialized_dy=serialized_dy)
        model_dir_name = os.path.basename(os.path.abspath(model_full_path))
        col_statement = ""
        # Only set column names if `ColSpec`
        if model_signature.inputs.has_input_names():
            col_names = model_signature.inputs.input_names()
            col_statement = f"df.columns = {col_names}"

        udf_code = _UDF_CODE_TEMPLATE.format(
            model_dir_name=model_dir_name,
            max_batch_size_string=max_batch_size_string,
            test_statements=test_statements,
            col_statement=col_statement,
        )
        is_permanent = False
        if stage_location:
            is_permanent = True
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=not persist_udf_file) as f:
            final_packages = ["pandas", "mlflow", "filelock"]
            if packages:
                final_packages = final_packages + packages
            f.write(udf_code)
            f.flush()
            if persist_udf_file:
                logger.info(f"Generated UDF file is persisted at: {f.name}")

            return session.udf.register_from_file(
                file_path=f.name,
                func_name="infer",
                name=f"{udf_name}",
                return_type=PandasSeriesType(snowpark_output_type),
                input_types=[PandasDataFrameType(snowpark_input_types)],
                replace=True,
                imports=[
                    f"{model_full_path}",
                    # TODO: pay attention to this
                    # if the file is moved, the path needs to be updated
                    # needed to use maxa library inside the udf
                    (str(Path(__file__).parent.parent), "maxa.regression"),
                    (str(Path(__file__).parent.parent.parent.parent.parent / "core/maxa/ds_core/"), "maxa.ds_core"),
                ],
                packages=final_packages,
                stage_location=stage_location,
                is_permanent=is_permanent,
            )


def _handle_package_versions(
    requirements_path: str,
    use_latest_package_version: bool,
) -> list[str]:
    requirements_lines = open(requirements_path).read().splitlines()
    try:
        return extract_package_requirements(
            requirements_lines=requirements_lines,
            exclusions={"mlflow", "mypy-extensions", "keyring", "jaraco-collections"},
            use_latest=use_latest_package_version,
        )
    except ValueError as e:
        raise MlflowException(str(e))


def upload_model_from_mlflow(
    session: Session,
    *,
    model_dir_path: str,
    udf_name: str,
    max_batch_size: Optional[int] = None,
    persist_udf_file: bool = True,
    test_data_X: Optional[pd.DataFrame] = None,
    test_data_y: Optional[pd.Series] = None,
    use_latest_package_version: bool = True,
    stage_location: Optional[str] = None,
):
    """Upload a supported model packaged by MLflow to be deployed as Snowflake Python UDF.

    The model file is automatically uploaded to stage from local temporary storage as part of the UDF registration.

    Args:
        session (Session): A Snowflake session object.
        model_dir_path (str): The model directory generated by MLflow run.
        udf_name (str): Name for the UDF.
        max_batch_size (int, optional): Maximum batch sizes for a single vectorized UDF invocation.
            The size is not guaranteed by Snowpark. Default to be None.
        persist_udf_file (bool, optional): Whether to keep the UDF file generated.
            Default to be False.
        test_data_X (pd.DataFrame, optional): 2d dataframe used as input test data.
        test_data_y (pd.Series, optional): 1d series used as expected prediction results.
            During testing, model predictions are compared with the expected predictions given in `test_data_y`.
            For comparing regression results, 1e-7 precision is used.
        use_latest_package_version (bool, optional):
            Whether to use latest package versions available in Snowlfake conda channel.
            Defaults to True. Settomg this flag to True will greatly increase the chance of successful deployment
            of the model to the Snowflake warehouse.
        stage_location (str, optional): Stage location to store the UDF and dependencies(format: `@my_named_stage`).
            It can be any stage other than temporary stages and external stages. If not specified,
            UDF deployment is temporary and tied to the session. Default to be none.
    """
    model_config_path = Path(model_dir_path) / _MLMODEL_FILE_NAME
    remove_required_in_signature(model_dir_path)
    if not model_config_path.exists():
        raise MlflowException("Model config file did not exist.")
    model_conf = Model.load(model_config_path)
    if model_conf.signature is None:
        raise MlflowException("Signature is required to automatically generate the UDF.")
    # if len(model_conf.signature.outputs.numpy_types()) != 1:
    #     raise MlflowException("Only single model output is supported.")
    is_test_data_X_set = test_data_X is not None
    is_test_data_y_set = test_data_y is not None
    if is_test_data_X_set and is_test_data_y_set:
        if test_data_X.shape[0] != test_data_y.shape[0]:
            raise MlflowException("Test data dimension mis-match.")
    elif is_test_data_X_set != is_test_data_y_set:
        raise MlflowException("Both input & output test data needs to be specified.")
    flavors = model_conf.flavors
    if not flavors:
        raise MlflowException("No flavor is specified for model deployment.")
    if PYFUNC_FLAVOR_NAME not in flavors:
        raise MlflowException("python_function flavor is required.")
    InferUDFHelper(model_dir_path, udf_name, use_latest_package_version, stage_location).generate_udf(
        session=session,
        max_batch_size=max_batch_size,
        persist_udf_file=persist_udf_file,
        test_data_X=test_data_X,
        test_data_y=test_data_y,
    )
