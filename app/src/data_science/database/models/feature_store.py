from sqlalchemy import ARRAY, JSON, Column, DateTime, String, func, text

from src.data_science.database.base import Base
from src.data_science.database.schema import SCHEMA_EXPERIMENT


class FeatureStore(Base):
    __tablename__ = "feature_store"
    __table_args__ = ({"schema": SCHEMA_EXPERIMENT},)
    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()::text"))
    feature_store_id = Column(String, nullable=False)
    experiment_id = Column(String, nullable=False)
    columns = Column(ARRAY(String))
    data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, server_default=func.current_user())
