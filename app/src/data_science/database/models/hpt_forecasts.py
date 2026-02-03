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
from src.data_science.database.schema import SCHEMA_EXPERIMENT


class HPTForecasts(Base):
    __tablename__ = "hpt_forecasts"
    __table_args__ = ({"schema": SCHEMA_EXPERIMENT},)
    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()::text"))
    run_id = Column(String, nullable=False)
    experiment_id = Column(String, nullable=False)
    feature_store_id = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    dim_uid = Column(JSON, nullable=False)
    features = Column(JSON)
    target_name = Column(String)
    target_value = Column(Float)
    prediction_name = Column(String)
    prediction_value = Column(Float)
    split = Column(String)
    fold = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, server_default=func.current_user())
