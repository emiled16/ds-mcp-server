from pydantic import BaseModel


class RunsConfig(BaseModel):
    feature_store_id: str | None = None
    runs_number: int
