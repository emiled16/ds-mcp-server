from sqlalchemy import (
    Column,
    DateTime,
    Float,
    String,
    func,
    text,
)

from src.data_science.database.base import Base
from src.data_science.database.schema import SCHEMA_EXPERIMENT


class HPTScores(Base):
    __tablename__ = "hpt_scores"
    __table_args__ = ({"schema": SCHEMA_EXPERIMENT},)
    id = Column(String, primary_key=True, server_default=text("uuid_string()"))
    run_id = Column(String, nullable=False)
    experiment_id = Column(String, nullable=False)
    feature_store_id = Column(String, nullable=False)
    score_name = Column(String)
    score_value = Column(Float)
    split = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, server_default=func.current_user())
