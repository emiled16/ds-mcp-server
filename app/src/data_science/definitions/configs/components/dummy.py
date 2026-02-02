from pydantic import BaseModel


class DummyRunConfig(BaseModel):
    experiment_name: str | None = None
    tracking_uri: str | None = None
    tags: dict | None = None
    input_cols: list[str]
    target_cols: list[str]
    output_cols: list[str]
