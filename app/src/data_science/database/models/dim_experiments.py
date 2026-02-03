from sqlalchemy import JSON, Column, DateTime, String, func, text

from src.data_science.database.base import Base
from src.data_science.database.schema import SCHEMA_EXPERIMENT


class DimExperiments(Base):
    __tablename__ = "dim_experiments"
    __table_args__ = ({"schema": SCHEMA_EXPERIMENT},)
    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()::text"))
    experiment_id = Column(String, nullable=False, server_default=text("gen_random_uuid()::text"))
    use_case_id = Column(String, nullable=False)
    name = Column(String)
    description = Column(String)
    config = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, server_default=func.current_user())
