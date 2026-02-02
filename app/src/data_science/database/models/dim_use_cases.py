from snowflake.sqlalchemy import OBJECT
from sqlalchemy import (
    Column,
    DateTime,
    String,
    func,
    text,
)

from src.data_science.database.base import Base
from src.data_science.database.schema import SCHEMA_EXPERIMENT


class DimUseCases(Base):
    __tablename__ = "dim_use_cases"
    __table_args__ = ({"schema": SCHEMA_EXPERIMENT},)
    id = Column(String, primary_key=True, server_default=text("uuid_string()"))
    use_case_id = Column(String, nullable=False, server_default=text("uuid_string()"))
    name = Column(String)
    description = Column(String)
    notes = Column(OBJECT)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, server_default=func.current_user())
