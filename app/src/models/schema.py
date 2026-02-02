"""Data schema models for validation."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ColumnType(str, Enum):
    """Supported column data types."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    CATEGORY = "category"


class ColumnSchema(BaseModel):
    """Schema definition for a single column."""

    name: str = Field(..., description="Column name")
    type: ColumnType = Field(..., description="Expected data type")
    nullable: bool = Field(True, description="Whether null values are allowed")
    min_value: float | None = Field(None, description="Minimum allowed value (numeric only)")
    max_value: float | None = Field(None, description="Maximum allowed value (numeric only)")
    allowed_values: list[Any] | None = Field(None, description="List of allowed values (categorical)")
    pattern: str | None = Field(None, description="Regex pattern for string validation")
    unique: bool = Field(False, description="Whether values must be unique")


class DataSchema(BaseModel):
    """Complete schema definition for a dataset."""

    name: str = Field(..., description="Schema name")
    description: str | None = Field(None, description="Schema description")
    columns: list[ColumnSchema] = Field(..., description="Column schemas")
    strict: bool = Field(False, description="Whether to reject extra columns not in schema")

    def get_column(self, name: str) -> ColumnSchema | None:
        """Get column schema by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None


class ValidationResult(BaseModel):
    """Result of data validation."""

    valid: bool = Field(..., description="Whether data is valid")
    errors: list[str] = Field(default_factory=list, description="List of validation errors")
    warnings: list[str] = Field(default_factory=list, description="List of validation warnings")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
