"""Validate dataset against a schema definition."""

import re

import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.schema import ColumnType, DataSchema, ValidationResult
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def validate_schema(
    dataset_id: str,
    schema: dict,
) -> str:
    """Validate dataset against a schema definition.

    Checks that the dataset conforms to the specified schema including:
    - Column presence and naming
    - Data types
    - Null value constraints
    - Value ranges (for numeric columns)
    - Allowed values (for categorical columns)
    - Pattern matching (for string columns)
    - Uniqueness constraints

    Args:
        dataset_id: Entity ID of the dataset to validate
        schema: Schema definition as dict (will be converted to DataSchema)
            Example:
            {
                "name": "sales_schema",
                "columns": [
                    {"name": "id", "type": "integer", "nullable": False, "unique": True},
                    {"name": "amount", "type": "float", "min_value": 0},
                    {"name": "category", "type": "category", "allowed_values": ["A", "B", "C"]}
                ],
                "strict": True
            }

    Returns:
        ToolResponse with validation results

    Example:
        "Validate the sales data against the sales schema"
        → validate_schema(
            dataset_id="sales_data_123",
            schema={
                "name": "sales_schema",
                "columns": [
                    {"name": "amount", "type": "float", "min_value": 0}
                ]
            }
        )
    """
    try:
        # Get dataset
        registry = get_repository_registry()
        entity = await registry.get("tool_response", dataset_id)

        if not entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Dataset '{dataset_id}' not found",
                metadata={"error": "NotFound", "dataset_id": dataset_id},
                storage_hint="never",
            )

        df = entity.payload
        if not isinstance(df, pd.DataFrame):
            return ToolResponse(
                payload=None,
                summary=f"Error: Entity '{dataset_id}' is not a DataFrame",
                metadata={"error": "TypeError", "entity_id": dataset_id},
                storage_hint="never",
            )

        # Parse schema
        try:
            data_schema = DataSchema(**schema)
        except Exception as e:
            return ToolResponse(
                payload=None,
                summary=f"Error: Invalid schema definition: {e}",
                metadata={"error": "SchemaError", "details": str(e)},
                storage_hint="never",
            )

        logger.info(f"Validating dataset with {len(df)} rows against schema '{data_schema.name}'")

        errors = []
        warnings = []

        # Check for missing columns
        schema_columns = {col.name for col in data_schema.columns}
        data_columns = set(df.columns)

        missing_columns = schema_columns - data_columns
        if missing_columns:
            errors.append(f"Missing required columns: {sorted(missing_columns)}")

        # Check for extra columns (if strict mode)
        if data_schema.strict:
            extra_columns = data_columns - schema_columns
            if extra_columns:
                errors.append(f"Unexpected columns (strict mode): {sorted(extra_columns)}")
        else:
            extra_columns = data_columns - schema_columns
            if extra_columns:
                warnings.append(f"Extra columns not in schema: {sorted(extra_columns)}")

        # Validate each column in schema
        for col_schema in data_schema.columns:
            col_name = col_schema.name

            # Skip if column is missing (already reported)
            if col_name not in df.columns:
                continue

            col_data = df[col_name]

            # Check nullability
            null_count = col_data.isnull().sum()
            if not col_schema.nullable and null_count > 0:
                errors.append(f"Column '{col_name}': {null_count} null values found (nullable=False)")
            elif null_count > 0:
                warnings.append(f"Column '{col_name}': {null_count} null values ({null_count / len(df) * 100:.1f}%)")

            # Check data type
            non_null_data = col_data.dropna()
            if len(non_null_data) > 0:
                expected_type = col_schema.type

                if expected_type == ColumnType.INTEGER:
                    if not pd.api.types.is_integer_dtype(col_data):
                        # Try to check if values are integers
                        try:
                            if not all(
                                non_null_data.apply(lambda x: isinstance(x, (int, float)) and float(x).is_integer())
                            ):
                                errors.append(f"Column '{col_name}': Expected integer type")
                        except Exception:
                            errors.append(f"Column '{col_name}': Expected integer type")

                elif expected_type == ColumnType.FLOAT:
                    if not pd.api.types.is_numeric_dtype(col_data):
                        errors.append(f"Column '{col_name}': Expected numeric type")

                elif expected_type == ColumnType.STRING:
                    if not pd.api.types.is_string_dtype(col_data) and not pd.api.types.is_object_dtype(col_data):
                        warnings.append(f"Column '{col_name}': Expected string type")

                elif expected_type == ColumnType.BOOLEAN:
                    if not pd.api.types.is_bool_dtype(col_data):
                        errors.append(f"Column '{col_name}': Expected boolean type")

                elif expected_type == ColumnType.DATETIME:
                    if not pd.api.types.is_datetime64_any_dtype(col_data):
                        errors.append(f"Column '{col_name}': Expected datetime type")

                elif expected_type == ColumnType.CATEGORY:
                    # Categories can be any type
                    pass

                # Check numeric range constraints
                if col_schema.min_value is not None or col_schema.max_value is not None:
                    if pd.api.types.is_numeric_dtype(col_data):
                        if col_schema.min_value is not None:
                            violations = (non_null_data < col_schema.min_value).sum()
                            if violations > 0:
                                errors.append(
                                    f"Column '{col_name}': {violations} values below min_value={col_schema.min_value}"
                                )

                        if col_schema.max_value is not None:
                            violations = (non_null_data > col_schema.max_value).sum()
                            if violations > 0:
                                errors.append(
                                    f"Column '{col_name}': {violations} values above max_value={col_schema.max_value}"
                                )

                # Check allowed values (categorical)
                if col_schema.allowed_values is not None:
                    invalid_values = set(non_null_data.unique()) - set(col_schema.allowed_values)
                    if invalid_values:
                        errors.append(f"Column '{col_name}': Invalid values found: {sorted(invalid_values)[:10]}")

                # Check pattern (string matching)
                if col_schema.pattern is not None:
                    try:
                        pattern = re.compile(col_schema.pattern)
                        non_matching = non_null_data.apply(lambda x: not bool(pattern.match(str(x)))).sum()
                        if non_matching > 0:
                            errors.append(
                                f"Column '{col_name}': {non_matching} values don't match pattern '{col_schema.pattern}'"
                            )
                    except Exception as e:
                        warnings.append(f"Column '{col_name}': Invalid regex pattern: {e}")

                # Check uniqueness
                if col_schema.unique:
                    duplicates = non_null_data.duplicated().sum()
                    if duplicates > 0:
                        errors.append(f"Column '{col_name}': {duplicates} duplicate values found (unique=True)")

        # Create validation result
        is_valid = len(errors) == 0
        validation_result = ValidationResult(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
            metadata={
                "schema_name": data_schema.name,
                "rows_checked": len(df),
                "columns_checked": len(data_schema.columns),
            },
        )

        # Generate summary
        summary = "📋 Schema Validation Results\n\n"
        summary += f"Schema: {data_schema.name}\n"
        summary += f"Dataset: {len(df):,} rows, {len(df.columns)} columns\n"
        summary += f"Status: {'✅ VALID' if is_valid else '❌ INVALID'}\n\n"

        if errors:
            summary += f"Errors ({len(errors)}):\n"
            for error in errors:
                summary += f"  ❌ {error}\n"
            summary += "\n"

        if warnings:
            summary += f"Warnings ({len(warnings)}):\n"
            for warning in warnings:
                summary += f"  ⚠️  {warning}\n"
            summary += "\n"

        if is_valid and not warnings:
            summary += "✅ All validation checks passed!\n"

        return ToolResponse(
            payload=validation_result.model_dump(),
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "schema_name": data_schema.name,
                "valid": is_valid,
            },
            storage_hint="session",
            suggested_name=f"validation_{data_schema.name}",
        )

    except Exception as e:
        logger.exception(f"Error validating schema: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error validating schema: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )
