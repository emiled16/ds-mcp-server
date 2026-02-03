from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
from loguru import logger
from pydantic import Field

from src.data_science.ds_core.definitions.orchestration.io import (
    BaseInput,
    BaseOutput,
    BaseParameter,
)
from src.data_science.ds_core.definitions.orchestration.step import BaseStep


class BaseTransformation(BaseStep, ABC):
    """Base class for all transformations in the system.

    This abstract class defines the interface and common functionality that all transformations
    must implement. It provides methods for fitting and transforming data using either Snowpark
    or Pandas engines, along with operator overloading for composition of transformations.

    Attributes:
        transformation (str): Type/category of the transformation
        description (str): Human-readable description of what the transformation does
        parameters (BaseVariable): Configuration parameters for the transformation
        inputs (List[BaseInput]): List of expected input variables, defaults to single DataFrame
        outputs (List[BaseOutput]): List of output variables, defaults to single DataFrame
        metadata (Dict[str, Any]): Additional metadata about the transformation
        is_fitted (bool): Whether the transformation has been fitted to data


    Example:
        ```python
        class MyTransformation(BaseTransformation):
            def _fit_snowpark(self, df, **kwargs):
                # Implementation for fitting with Snowpark
                return self

            def _transform_snowpark(self, df, **kwargs):
                # Implementation for transforming with Snowpark
                return df

            # Similar implementations for _fit_pandas and _transform_pandas
        ```
    """

    name: str
    display_name: str | None = None
    description: str
    parameters: list[BaseParameter] | None = Field(default=None)
    inputs: list[BaseInput] = Field(default=[BaseInput()])
    outputs: list[BaseOutput] = Field(default=[BaseOutput()])
    is_fitted: bool = False

    def model_dump(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "parameters": [p.model_dump() for p in self.parameters] if self.parameters else None,
            "inputs": [i.model_dump() for i in self.inputs] if self.inputs else None,
            "outputs": [o.model_dump() for o in self.outputs] if self.outputs else None,
            "is_fitted": self.is_fitted,
        }

    @classmethod
    def get_description(cls) -> str:
        description = cls.model_fields.get("description")
        if description is None:
            return ""
        return description.default

    @classmethod
    def get_name(cls) -> str:
        name = cls.model_fields.get("name")
        if name is None:
            return ""
        return name.default

    @classmethod
    def get_parameters(cls) -> dict[str, str]:
        res = {}
        parameters = cls.model_fields.get("parameters")
        if parameters is None:
            return res
        for k, v in parameters.annotation.model_fields.items():
            res[k] = v.description
        return res

    def fit(
        self,
        **inputs: pd.DataFrame,
    ) -> "BaseTransformation":
        self.validate_inputs(**inputs)
        self._fit_pandas(**inputs)
        self.is_fitted = True
        return self

    def transform(
        self,
        **inputs: pd.DataFrame,
    ) -> pd.DataFrame:
        self.validate_inputs(**inputs)
        result = self._transform_pandas(**inputs)

        logger.info("Shape of output after transformation:")
        logger.info(result.shape)
        logger.info(f"Duplicates after result: {result.duplicated().sum()}")

        return result

    def fit_transform(
        self,
        **inputs: pd.DataFrame,
    ) -> pd.DataFrame:
        return self.fit(**inputs).transform(**inputs)

    @abstractmethod
    def _fit_snowpark(self, **inputs: Any) -> "BaseTransformation":
        raise NotImplementedError("This transformation does not support Snowpark")

    @abstractmethod
    def _fit_pandas(self, **inputs: pd.DataFrame) -> "BaseTransformation": ...

    @abstractmethod
    def _transform_snowpark(self, **inputs: Any) -> Any:
        raise NotImplementedError("This transformation does not support Snowpark")

    @abstractmethod
    def _transform_pandas(self, **inputs: pd.DataFrame) -> pd.DataFrame: ...
