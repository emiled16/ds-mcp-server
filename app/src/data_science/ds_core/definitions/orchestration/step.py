from abc import ABC
from typing import Literal, Optional, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from src.data_science.compat import SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.io import BaseInput, BaseOutput, BaseParameter


class BaseStep(BaseModel, ABC):
    name: str = Field(description="Name of the step")
    description: str = Field(description="Description of the step")
    inputs: Optional[list[BaseInput]] = Field(default=None)
    outputs: Optional[list[BaseOutput]] = Field(default=None)
    parameters: Optional[list[BaseParameter]] = Field(default=None)
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def validate_inputs(self, **kwargs) -> bool:
        # - validate that all required inputs are present, with correct types
        # - flag any additional inputs that are present but not required
        errors = {}
        for required_input in self.inputs or []:
            if required_input.name not in kwargs:
                errors[required_input.name] = f"Missing input of type {required_input.type}"
            elif not isinstance(kwargs[required_input.name], required_input.type):
                errors[required_input.name] = f"Incorrect type, should be {required_input.type}"
        if errors:
            raise ValueError(errors)
        return True

    @staticmethod
    def _find_engine(
        inputs: dict[str, Union[pd.DataFrame, SnowparkDataFrame]],
    ) -> Literal["pandas", "snowpark"]:
        all_pandas = all(isinstance(x, pd.DataFrame) for x in inputs.values())
        all_snowpark = all(isinstance(x, SnowparkDataFrame) for x in inputs.values())
        if all_pandas:
            return "pandas"
        if all_snowpark:
            return "snowpark"
        raise ValueError("All inputs must be of the same type")
