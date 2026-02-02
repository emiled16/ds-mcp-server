from pydantic import BaseModel


class ExperimentsConfig(BaseModel):
    experiment_name: str
    use_case_id: str
    tags: dict[str, str]
    description: str | None = None
    tracking_uri: str = "file:///tmp/mlruns"
    backend_storage_uri: str | None = None
