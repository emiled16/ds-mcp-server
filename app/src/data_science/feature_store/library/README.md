# Feature Store Library

## Overview

The feature store library is a library that allows you to create,update, and maintain features/transformations.


## Transformations:
<!-- write a table of all transformations, with the inputs and outputs and a description -->
| Name | Description | Inputs | Outputs |
|------|-------------|--------|---------|
| Lag | Add lags to a dataframe | df, lags | df |
| Aggregation | Aggregate data based on dimensions and metrics | df, dimensions, aggregation | df |
| RenameColumns | Rename columns in a dataframe | df, columns | df |
| SelectCols | Select columns in a dataframe | df, columns | df |
| TruncDate | Truncate a date column to a unit | df, column, unit | df |
| Union | Union two dataframes | df1, df2 | df |
| Identity | Identity transformation | df | df |
| Optional | Optional transformation | df | df |


## How to create your own custom transformation:

1. Create a new file library/transformations/your_transformation.py
2. Create a Parameters class that inherits from BaseParameter and add the parameters needed for your transformation.
```python
class YourTransformationParameters(BaseParameter):
    param1: str = Field(..., description="Description of param1")
    ...
```
3. Inherit from BaseTransformation and implement the _transform_pandas and _transform_snowpark methods. Modify the inputs and outputs as needed. Inputs and outputs should be of type Union[pd.DataFrame, SnowparkDataFrame] and should inherit from the BaseTransformation class.
```python
from typing import Dict, List, Literal, Union

import pandas as pd
from pydantic import Field

import snowflake.snowpark.functions as f
from snowflake.snowpark import DataFrame as SnowparkDataFrame
from src.definitions.transformations.base import BaseParameter, BaseTransformation


class YourTransformationInput(BaseInput):
    name: str = Field(default="NAME_OF_INPUT")
    description: str = Field(default="DESCRIPTION_OF_INPUT")
    type: Any = Field(
        description="Type of the input",
        default=Union[pd.DataFrame, SnowparkDataFrame],
    )

class YourTransformationOutput(BaseOutput):
    name: str = Field(default="NAME_OF_OUTPUT")
    description: str = Field(default="DESCRIPTION_OF_OUTPUT")
    type: Any = Field(
        description="Type of the output",
        default=Union[pd.DataFrame, SnowparkDataFrame],
    )


class YourTransformation(BaseTransformation):
    transformation: Literal["YourTransformation"] = "YourTransformation"
    description: str = "Description of the transformation"
    parameters: YourTransformationParameters
    inputs: List[YourTransformationInput] = Field(default_factory=[YourTransformationInput(), ...])
    outputs: List[YourTransformationOutput] = Field(default_factory=[YourTransformationOutput(), ...])

    def _fit_pandas(self, df: pd.DataFrame) -> "YourTransformation":
        ...

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        ...

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "YourTransformation":
        ...

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        ...
```
4. Add the transformation to the library by adding it to the __init__.py file.
```python
from library.transformations.your_transformation import YourTransformation

__all__ = [..., "YourTransformation"]
```
