import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MetricConfig(BaseModel):
    column: str
    aggregation_method: str
    name: str


Periodicity = Literal["daily", "weekly", "monthly", "quarterly", "yearly"]


class TimeSeriesConfig(BaseModel):
    date_column: str
    ascending: bool
    dimensions: list[str] | None = Field(default_factory=list)
    metrics: MetricConfig
    last_test_date: str
    periodicity: Periodicity

    @model_validator(mode="after")
    def set_dimensions(self) -> "TimeSeriesConfig":
        if self.dimensions is None:
            self.dimensions = []
        return self

    @model_validator(mode="after")
    def assert_last_test_date(self) -> "TimeSeriesConfig":
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", self.last_test_date):
            raise ValueError("last_test_date must be in the format YYYY-MM-DD")
        return self
