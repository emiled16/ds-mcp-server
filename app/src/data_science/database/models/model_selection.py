from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    String,
    func,
    text,
)

from src.data_science.database.base import Base
from src.data_science.database.schema import SCHEMA_EXPERIMENT


class ModelSelection(Base):
    __tablename__ = "model_selection"
    __table_args__ = ({"schema": SCHEMA_EXPERIMENT},)
    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()::text"))
    model_selection_id = Column(String, nullable=False, server_default=text("gen_random_uuid()::text"))
    run_id = Column(String, nullable=False)
    experiment_id = Column(String, nullable=False)
    feature_store_id = Column(String, nullable=False)
    model_name = Column(String)
    model_config = Column(JSON)
    pipeline_path = Column(String)
    model_path = Column(String)
    status = Column(String, nullable=False)
    notes = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, server_default=func.current_user())
