"""List available transformations tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse

# Transformation catalog - describes available transformations
TRANSFORMATION_CATALOG = {
    "Lag": {
        "display_name": "Create Lagged Features",
        "description": "Add lagged versions of columns for time series analysis",
        "parameters": {
            "lags": "dict[str, list[int]] - Column names mapped to lag periods",
            "columns_to_order_by": "list[str] - Columns to sort by before lagging",
            "columns_to_partition_by": "list[str] - Columns to partition/group by",
            "fillna": "bool - Whether to fill NaN values with 0 (default: True)",
        },
        "example": {
            "transformation": "Lag",
            "parameters": {
                "lags": {"sales": [1, 7, 30]},
                "columns_to_order_by": ["date"],
                "columns_to_partition_by": ["product_id"],
            },
        },
    },
    "Aggregation": {
        "display_name": "Aggregate Data",
        "description": "Aggregate data by grouping dimensions and computing metrics",
        "parameters": {
            "dimensions": "list[str] - Columns to group by",
            "metrics": "dict[str, str] - Column names mapped to aggregation function (sum, avg, min, max, count)",
        },
        "example": {
            "transformation": "Aggregation",
            "parameters": {
                "dimensions": ["product_id", "region"],
                "metrics": {"sales": "sum", "quantity": "avg"},
            },
        },
    },
    "SelectCols": {
        "display_name": "Select Columns",
        "description": "Select specific columns from the dataset",
        "parameters": {
            "columns": "list[str] - Column names to keep",
        },
        "example": {
            "transformation": "SelectCols",
            "parameters": {"columns": ["product_id", "date", "sales"]},
        },
    },
    "DropCols": {
        "display_name": "Drop Columns",
        "description": "Remove specified columns from the dataset",
        "parameters": {
            "columns": "list[str] - Column names to drop",
        },
        "example": {
            "transformation": "DropCols",
            "parameters": {"columns": ["temp_col", "debug_col"]},
        },
    },
    "RenameColumns": {
        "display_name": "Rename Columns",
        "description": "Rename columns in the dataset",
        "parameters": {
            "columns": "dict[str, str] - Old names mapped to new names",
        },
        "example": {
            "transformation": "RenameColumns",
            "parameters": {"columns": {"old_name": "new_name"}},
        },
    },
    "FillColsValues": {
        "display_name": "Fill Missing Values",
        "description": "Fill missing values with specified values or methods",
        "parameters": {
            "fill_values": "dict[str, Any] - Column names mapped to fill values",
            "fill_method": "str - Fill method ('ffill', 'bfill', or None)",
        },
        "example": {
            "transformation": "FillColsValues",
            "parameters": {"fill_values": {"price": 0, "category": "unknown"}},
        },
    },
    "DropRowsNA": {
        "display_name": "Drop Rows with Missing Values",
        "description": "Remove rows containing null values",
        "parameters": {
            "columns": "list[str] - Columns to check for nulls (default: all)",
            "how": "str - 'any' or 'all' (default: 'any')",
        },
        "example": {
            "transformation": "DropRowsNA",
            "parameters": {"columns": ["price", "quantity"], "how": "any"},
        },
    },
    "DropRowsDuplicates": {
        "display_name": "Drop Duplicate Rows",
        "description": "Remove duplicate rows",
        "parameters": {
            "columns": "list[str] - Columns to consider for duplicates",
            "keep": "str - 'first', 'last', or False",
        },
        "example": {
            "transformation": "DropRowsDuplicates",
            "parameters": {"columns": ["product_id", "date"], "keep": "first"},
        },
    },
    "FilterRows": {
        "display_name": "Filter Rows",
        "description": "Filter rows based on conditions",
        "parameters": {
            "filter_expression": "str - Filter condition expression",
        },
        "example": {
            "transformation": "FilterRows",
            "parameters": {"filter_expression": "sales > 100"},
        },
    },
    "ScalingNumerical": {
        "display_name": "Scale Numerical Features",
        "description": "Scale numerical columns using standard or min-max scaling",
        "parameters": {
            "columns": "list[str] - Columns to scale",
            "method": "str - 'standard' (z-score) or 'minmax' (0-1)",
        },
        "example": {
            "transformation": "ScalingNumerical",
            "parameters": {"columns": ["price", "quantity"], "method": "standard"},
        },
    },
    "EncodeOneHot": {
        "display_name": "One-Hot Encode",
        "description": "One-hot encode categorical columns",
        "parameters": {
            "columns": "list[str] - Categorical columns to encode",
            "drop_first": "bool - Whether to drop first category (default: False)",
        },
        "example": {
            "transformation": "EncodeOneHot",
            "parameters": {"columns": ["category", "region"], "drop_first": True},
        },
    },
    "CyclicalTimeTransform": {
        "display_name": "Cyclical Time Encoding",
        "description": "Encode time features as cyclical (sin/cos) for periodicity",
        "parameters": {
            "column": "str - Column containing time values",
            "period": "int - Period of the cycle (e.g., 12 for months, 7 for days of week)",
        },
        "example": {
            "transformation": "CyclicalTimeTransform",
            "parameters": {"column": "month", "period": 12},
        },
    },
    "MathsTransform": {
        "display_name": "Mathematical Transformation",
        "description": "Apply mathematical operations to columns (log, sqrt, square, etc.)",
        "parameters": {
            "columns": "list[str] - Columns to transform",
            "operation": "str - 'log', 'log1p', 'sqrt', 'square', 'exp'",
        },
        "example": {
            "transformation": "MathsTransform",
            "parameters": {"columns": ["sales"], "operation": "log1p"},
        },
    },
    "PolynomialFeatures": {
        "display_name": "Polynomial Features",
        "description": "Create polynomial and interaction features",
        "parameters": {
            "columns": "list[str] - Columns to create features from",
            "degree": "int - Polynomial degree (default: 2)",
            "interaction_only": "bool - Only interaction features (default: False)",
        },
        "example": {
            "transformation": "PolynomialFeatures",
            "parameters": {"columns": ["x1", "x2"], "degree": 2},
        },
    },
    "Sort": {
        "display_name": "Sort Data",
        "description": "Sort the dataset by specified columns",
        "parameters": {
            "columns": "list[str] - Columns to sort by",
            "ascending": "bool or list[bool] - Sort order",
        },
        "example": {
            "transformation": "Sort",
            "parameters": {"columns": ["date", "product_id"], "ascending": [True, True]},
        },
    },
}


@mcp.tool
@process_tool
@register_tool
async def list_available_transformations(category: str | None = None) -> str:
    """List all available data transformations.

    Shows transformations that can be applied to datasets using apply_transformation().
    Each transformation includes parameters and usage examples.

    Args:
        category: Optional category filter:
            - 'feature': Feature engineering (Lag, Polynomial, Cyclical)
            - 'cleaning': Data cleaning (Fill, Drop, Filter)
            - 'encoding': Encoding (OneHot, Scaling)
            - 'structure': Structural (Select, Rename, Sort)

    Returns:
        ToolResponse with transformation catalog

    Example:
        "What transformations are available?"
        → list_available_transformations()

        "Show feature engineering transformations"
        → list_available_transformations(category="feature")
    """
    # Categorize transformations
    categories = {
        "feature": ["Lag", "PolynomialFeatures", "CyclicalTimeTransform", "MathsTransform", "Aggregation"],
        "cleaning": ["FillColsValues", "DropRowsNA", "DropRowsDuplicates", "FilterRows", "DropCols"],
        "encoding": ["EncodeOneHot", "ScalingNumerical"],
        "structure": ["SelectCols", "RenameColumns", "Sort"],
    }

    # Filter by category if specified
    if category:
        category = category.lower()
        if category not in categories:
            valid = list(categories.keys())
            return ToolResponse(
                payload=None,
                summary=f"Invalid category '{category}'. Valid options: {valid}",
                metadata={"error": "InvalidCategory", "valid": valid},
                storage_hint="never",
            )
        filter_names = categories[category]
        filtered = {k: v for k, v in TRANSFORMATION_CATALOG.items() if k in filter_names}
    else:
        filtered = TRANSFORMATION_CATALOG

    # Build summary
    summary = "# Available Transformations\n\n"

    for cat_name, cat_transforms in categories.items():
        if category and cat_name != category:
            continue

        available = [t for t in cat_transforms if t in filtered]
        if not available:
            continue

        cat_display = cat_name.replace("_", " ").title()
        summary += f"## {cat_display}\n\n"

        for transform_name in available:
            info = filtered[transform_name]
            summary += f"### {transform_name}\n"
            summary += f"**{info['display_name']}**: {info['description']}\n\n"

            summary += "Parameters:\n"
            for param_name, param_desc in info["parameters"].items():
                summary += f"  • `{param_name}`: {param_desc}\n"

            summary += "\nExample:\n```json\n"
            import json

            summary += json.dumps(info["example"], indent=2)
            summary += "\n```\n\n"

    summary += f"\nTotal: {len(filtered)} transformations\n"
    summary += "\nUse apply_transformation(entity_id='...', transformation={...}) to apply."

    return ToolResponse(
        payload={
            "transformations": filtered,
            "categories": categories,
            "total": len(filtered),
        },
        summary=summary,
        metadata={"category": category, "total": len(filtered)},
        storage_hint="never",
    )
