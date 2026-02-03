from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    String,
    func,
    text,
)

from src.data_science.database.base import Base
from src.data_science.database.schema import SCHEMA_INFERENCE


class Inference(Base):
    __tablename__ = "inference"
    __table_args__ = ({"schema": SCHEMA_INFERENCE},)
    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()::text"))
    inference_id = Column(String, nullable=False)
    experiment_id = Column(String, nullable=False)
    dimensions = Column(JSON)
    date = Column(DateTime)
    features = Column(JSON)
    prediction_name = Column(String)
    prediction_value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, server_default=func.current_user())
