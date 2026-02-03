import json
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class BaseVariable(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
    name: str
    description: str
    type: type[Any]

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
        default=pd.DataFrame,
    )


class BaseOutput(BaseVariable):
    name: str = Field(default="df")
    description: str = Field(default="Output of the transformation")
    type: Any = Field(
        description="Type of the output",
        default=pd.DataFrame,
    )
