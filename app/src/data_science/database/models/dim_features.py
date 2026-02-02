from snowflake.sqlalchemy import OBJECT
from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    String,
    func,
    text,
)

from src.data_science.database.base import Base
from src.data_science.database.schema import SCHEMA_EXPERIMENT


class DimFeatures(Base):
    __tablename__ = "dim_features"
    __table_args__ = ({"schema": SCHEMA_EXPERIMENT},)
    id = Column(String, primary_key=True, server_default=text("uuid_string()"))
    feature_store_id = Column(String, nullable=False, server_default=text("uuid_string()"))
    experiment_id = Column(String, nullable=False)
    name = Column(String)
    notes = Column(String)
    config = Column(OBJECT)
    columns = Column(ARRAY(String))
    pipeline_path = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, server_default=func.current_user())
