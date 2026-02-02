import json
from typing import Any, Type, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame


class BaseVariable(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
    name: str
    description: str
    type: Type[Any]

    def __hash__(self) -> int:
        dump = self.model_dump(exclude={"type"})
        dump["type"] = str(self.type)
        return hash(json.dumps(dump))


class BaseParameter(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class BaseInput(BaseVariable):
    name: str = Field(default="df")
    description: str = Field(default="Dataframe to transform")
    type: Any = Field(
        description="Type of the input",
        default=Union[pd.DataFrame, SnowparkDataFrame],
    )


class BaseOutput(BaseVariable):
    name: str = Field(default="df")
    description: str = Field(default="Output of the transformation")
    type: Any = Field(
        description="Type of the output",
        default=Union[pd.DataFrame, SnowparkDataFrame],
    )
