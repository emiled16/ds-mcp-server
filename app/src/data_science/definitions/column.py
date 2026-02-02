from typing import Literal

from pydantic import BaseModel


class Column(BaseModel):
    name: str
    target_name: str
    type: Literal["str", "datetime64[ns]", "int", "boolean", "float"]
