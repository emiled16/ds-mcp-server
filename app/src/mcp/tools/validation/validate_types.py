"""Validate column data types in a dataset."""

import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def validate_types(
    dataset_id: str,
    expected_types: dict[str, str] | None = None,
) -> str:
    """Validate column data types in a dataset.

    Checks the actual data types of columns and optionally compares them
    to expected types. Useful for catching type mismatches before processing.

    Args:
        dataset_id: Entity ID of the dataset to validate
        expected_types: Optional dictionary mapping column names to expected types
            Supported types: "integer", "float", "string", "boolean", "datetime", "object"
            Example: {"age": "integer", "name": "string", "created_at": "datetime"}

    Returns:
        ToolResponse with type validation results

    Example:
        "Check the data types in the customer dataset"
        → validate_types(dataset_id="customer_data_123")

        "Validate that age is integer and name is string"
        → validate_types(
            dataset_id="customer_data_123",
            expected_types={"age": "integer", "name": "string"}
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

        logger.info(f"Validating types for dataset with {len(df)} rows, {len(df.columns)} columns")

        # Get actual types
        actual_types = {}
        for col in df.columns:
            dtype = df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                actual_types[col] = "integer"
            elif pd.api.types.is_float_dtype(dtype):
                actual_types[col] = "float"
            elif pd.api.types.is_bool_dtype(dtype):
                actual_types[col] = "boolean"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                actual_types[col] = "datetime"
            elif pd.api.types.is_string_dtype(dtype):
                actual_types[col] = "string"
            else:
                actual_types[col] = "object"

        # Compare with expected types if provided
        mismatches = []
        if expected_types:
            for col_name, expected_type in expected_types.items():
                if col_name not in df.columns:
                    mismatches.append(
                        {
                            "column": col_name,
                            "error": "Column not found",
                            "expected": expected_type,
                            "actual": None,
                        }
                    )
                elif actual_types[col_name] != expected_type:
                    mismatches.append(
                        {
                            "column": col_name,
                            "error": "Type mismatch",
                            "expected": expected_type,
                            "actual": actual_types[col_name],
                        }
                    )

        # Generate summary
        summary = "📊 Data Type Validation\n\n"
        summary += f"Dataset: {len(df):,} rows, {len(df.columns)} columns\n\n"

        if expected_types:
            is_valid = len(mismatches) == 0
            summary += f"Status: {'✅ VALID' if is_valid else '❌ INVALID'}\n\n"

            if mismatches:
                summary += f"Type Mismatches ({len(mismatches)}):\n"
                for mismatch in mismatches:
                    summary += (
                        f"  ❌ {mismatch['column']}: Expected '{mismatch['expected']}', got '{mismatch['actual']}'\n"
                    )
                summary += "\n"

            # Show matching types
            matching = [col for col in expected_types if col in df.columns and actual_types[col] == expected_types[col]]
            if matching:
                summary += f"Correct Types ({len(matching)}):\n"
                for col in matching[:10]:  # Show first 10
                    summary += f"  ✅ {col}: {expected_types[col]}\n"
                if len(matching) > 10:
                    summary += f"  ... and {len(matching) - 10} more\n"
                summary += "\n"
        else:
            is_valid = True
            summary += "Detected Column Types:\n"
            for col, dtype in actual_types.items():
                summary += f"  • {col}: {dtype}\n"

        result_data = {
            "actual_types": actual_types,
            "expected_types": expected_types,
            "mismatches": mismatches,
            "valid": is_valid if expected_types else None,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "n_columns": len(df.columns),
                "valid": is_valid if expected_types else None,
            },
            storage_hint="session",
            suggested_name="type_validation",
        )

    except Exception as e:
        logger.exception(f"Error validating types: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error validating types: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )
