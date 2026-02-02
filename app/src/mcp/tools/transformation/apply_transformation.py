"""Apply transformation tool."""

import pandas as pd

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry

# Constants
MAX_COLS_DISPLAY = 10


# Import transformations from the feature store library
AVAILABLE_TRANSFORMATIONS = {}

try:
    from src.data_science.feature_store.library.transformations import (
        Aggregation,
        CastTypes,
        CyclicalTimeTransform,
        DropCols,
        DropColsZeroVar,
        DropOutliersIQR,
        DropRareLabels,
        DropRowsDuplicates,
        DropRowsNA,
        DropRowsOutOfBounds,
        EncodeOneHot,
        FeatureAgglomeration,
        FillColsValues,
        FilterRows,
        Lag,
        MathsTransform,
        PolynomialFeatures,
        ReductionPCA,
        RenameColumns,
        ScalingNumerical,
        SelectCols,
        Sort,
    )

    AVAILABLE_TRANSFORMATIONS = {
        "Lag": Lag,
        "Aggregation": Aggregation,
        "SelectCols": SelectCols,
        "DropCols": DropCols,
        "RenameColumns": RenameColumns,
        "FillColsValues": FillColsValues,
        "DropRowsNA": DropRowsNA,
        "DropRowsDuplicates": DropRowsDuplicates,
        "FilterRows": FilterRows,
        "ScalingNumerical": ScalingNumerical,
        "EncodeOneHot": EncodeOneHot,
        "CyclicalTimeTransform": CyclicalTimeTransform,
        "MathsTransform": MathsTransform,
        "PolynomialFeatures": PolynomialFeatures,
        "Sort": Sort,
        "CastTypes": CastTypes,
        "DropColsZeroVar": DropColsZeroVar,
        "DropOutliersIQR": DropOutliersIQR,
        "DropRareLabels": DropRareLabels,
        "DropRowsOutOfBounds": DropRowsOutOfBounds,
        "FeatureAgglomeration": FeatureAgglomeration,
        "ReductionPCA": ReductionPCA,
    }
except ImportError:
    # Transformations not available - will use basic pandas operations
    pass


@mcp.tool
@process_tool
@register_tool
async def apply_transformation(
    entity_id: str,
    transformation: dict,
) -> str:
    """Apply a transformation to a dataset.

    Applies feature engineering or data transformations using the
    feature store library. Use list_available_transformations() to
    see all available transformations and their parameters.

    Args:
        entity_id: Entity ID of the dataset to transform
        transformation: Transformation config with 'name' and 'parameters':
            {
                "name": "Lag",  # Transformation name
                "parameters": {  # Transformation-specific parameters
                    "lags": {"sales": [1, 7]},
                    "columns_to_order_by": ["date"]
                }
            }

    Returns:
        ToolResponse with transformed dataset

    Example:
        "Add lag features to the sales data"
        → apply_transformation(
            entity_id="abc123",
            transformation={
                "name": "Lag",
                "parameters": {
                    "lags": {"sales": [1, 7, 30]},
                    "columns_to_order_by": ["date"],
                    "columns_to_partition_by": ["product_id"]
                }
            }
        )

        "Scale the price and quantity columns"
        → apply_transformation(
            entity_id="abc123",
            transformation={
                "name": "ScalingNumerical",
                "parameters": {
                    "columns": ["price", "quantity"],
                    "method": "standard"
                }
            }
        )
    """
    try:
        # Get dataset
        registry = get_repository_registry()
        entity = await registry.get("tool_response", entity_id)

        if not entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Dataset '{entity_id}' not found.",
                metadata={"error": "NotFound", "entity_id": entity_id},
                storage_hint="never",
            )

        df = entity.payload
        if not isinstance(df, pd.DataFrame):
            return ToolResponse(
                payload=None,
                summary=f"Error: Entity '{entity_id}' is not a DataFrame.",
                metadata={"error": "TypeError", "entity_id": entity_id},
                storage_hint="never",
            )

        # Parse transformation config
        transform_name = transformation.get("name")
        transform_params = transformation.get("parameters", {})

        if not transform_name:
            return ToolResponse(
                payload=None,
                summary="Error: Transformation config must include 'name' field.\n"
                "Use list_available_transformations() to see available options.",
                metadata={"error": "ValidationError"},
                storage_hint="never",
            )

        # Check if transformation is available
        if transform_name not in AVAILABLE_TRANSFORMATIONS:
            available = list(AVAILABLE_TRANSFORMATIONS.keys())
            return ToolResponse(
                payload=None,
                summary=f"Error: Transformation '{transform_name}' not found.\n"
                f"Available: {', '.join(available[:10])}...\n"
                "Use list_available_transformations() for details.",
                metadata={"error": "NotFound", "available": available},
                storage_hint="never",
            )

        # Create transformation instance
        transform_class = AVAILABLE_TRANSFORMATIONS[transform_name]

        # Build parameters based on transformation type
        try:
            # Create the transformation with parameters
            param_class = transform_class.model_fields.get("parameters")
            if param_class and transform_params:
                # Get the parameter class from the transformation
                param_type = param_class.annotation
                params = param_type(**transform_params)
                transform = transform_class(parameters=params)
            else:
                transform = transform_class(**transform_params)
        except (TypeError, ValueError) as e:
            return ToolResponse(
                payload=None,
                summary=f"Error creating transformation: {e}\nCheck parameter names and types.",
                metadata={"error": "ParameterError", "details": str(e)},
                storage_hint="never",
            )

        # Apply transformation
        original_shape = df.shape
        try:
            # fit_transform takes **kwargs, so pass df as keyword argument
            result_df = transform.fit_transform(df=df)
        except Exception as e:
            return ToolResponse(
                payload=None,
                summary=f"Error applying transformation: {e}",
                metadata={"error": "TransformError", "details": str(e)},
                storage_hint="never",
            )

        # Generate summary
        new_shape = result_df.shape
        new_cols = set(result_df.columns) - set(df.columns)
        removed_cols = set(df.columns) - set(result_df.columns)

        summary = f"Applied '{transform_name}' transformation:\n\n"
        summary += f"Original shape: {original_shape[0]:,} rows × {original_shape[1]} columns\n"
        summary += f"Result shape: {new_shape[0]:,} rows × {new_shape[1]} columns\n"

        if new_cols:
            summary += f"\nNew columns ({len(new_cols)}): {', '.join(list(new_cols)[:MAX_COLS_DISPLAY])}"
            if len(new_cols) > MAX_COLS_DISPLAY:
                summary += f"... +{len(new_cols) - MAX_COLS_DISPLAY} more"
            summary += "\n"

        if removed_cols:
            summary += f"\nRemoved columns ({len(removed_cols)}): {', '.join(list(removed_cols)[:MAX_COLS_DISPLAY])}"
            if len(removed_cols) > MAX_COLS_DISPLAY:
                summary += f"... +{len(removed_cols) - MAX_COLS_DISPLAY} more"
            summary += "\n"

        # Preview
        preview = result_df.head(3).to_string(max_cols=10, max_colwidth=30)
        summary += f"\nPreview:\n{preview}"

        suggested_name = f"{entity.suggested_name or 'data'}_{transform_name.lower()}"

        return ToolResponse(
            payload=result_df,
            summary=summary,
            metadata={
                "entity_id": entity_id,
                "transformation": transform_name,
                "parameters": transform_params,
                "original_shape": original_shape,
                "result_shape": new_shape,
                "new_columns": list(new_cols),
                "removed_columns": list(removed_cols),
            },
            storage_hint="session",
            suggested_name=suggested_name,
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error applying transformation: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )
