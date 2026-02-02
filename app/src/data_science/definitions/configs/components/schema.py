from pydantic import BaseModel


class Features(BaseModel):
    mandatory: list[str]
    optional: list[str]


class SchemaConfig(BaseModel):
    index: list[str] | None = None
    dimensions: list[str] | None = None
    date: str
    target: str
    features: Features
