"""Load CSV file tool."""

import pandas as pd

from src.constants import DATASET_PATH
from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse


@mcp.tool
@process_tool
@register_tool
async def load_csv(filename: str, nrows: int | None = None) -> str:
    """Load a CSV file from the datasets folder.

    Loads a CSV file and returns a summary with shape, column names, and memory usage.
    The full DataFrame is stored for use in subsequent operations.

    Args:
        filename: Name of the CSV file (e.g., 'sales.csv')
        nrows: Optional number of rows to load (for previewing large files)

    Returns:
        ToolResponse with DataFrame in payload and summary statistics

    Example:
        "Load the sales.csv file"
        → load_csv(filename="sales.csv")

        "Preview first 1000 rows of large_data.csv"
        → load_csv(filename="large_data.csv", nrows=1000)
    """
    file_path = DATASET_PATH / filename

    if not file_path.exists():
        return ToolResponse(
            payload=None,
            summary=f"Error: File '{filename}' not found in datasets folder.\n"
            f"Available files can be listed with list_available_datasets().",
            metadata={"error": "FileNotFoundError", "filename": filename},
            storage_hint="never",
        )

    try:
        # Load CSV with optional row limit
        df = pd.read_csv(file_path, nrows=nrows)

        # Generate column type summary
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

        # Create column list (truncate if too many)
        max_cols_display = 15
        col_display = df.columns.tolist()
        if len(col_display) > max_cols_display:
            col_display = col_display[:max_cols_display] + [f"... +{len(df.columns) - max_cols_display} more"]

        # Memory usage
        memory_mb = df.memory_usage(deep=True).sum() / 1024**2

        # Generate summary
        summary = (
            f"Loaded '{filename}' successfully:\n"
            f"  • Rows: {len(df):,}" + (f" (limited to {nrows})" if nrows else "") + "\n"
            f"  • Columns: {len(df.columns)}\n"
            f"  • Column names: {', '.join(col_display)}\n"
            f"  • Column types:\n"
            f"    - Numeric: {len(numeric_cols)} ({', '.join(numeric_cols[:5])}{' ...' if len(numeric_cols) > 5 else ''})\n"
            f"    - Categorical: {len(categorical_cols)} ({', '.join(categorical_cols[:5])}{' ...' if len(categorical_cols) > 5 else ''})\n"
            f"    - Datetime: {len(datetime_cols)}\n"
            f"  • Memory usage: {memory_mb:.2f} MB"
        )

        # Add preview of first few rows
        preview = df.head(3).to_string(max_cols=10, max_colwidth=30)
        summary += f"\n\nPreview (first 3 rows):\n{preview}"

        return ToolResponse(
            payload=df,
            summary=summary,
            metadata={
                "filename": filename,
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "memory_mb": memory_mb,
                "numeric_columns": numeric_cols,
                "categorical_columns": categorical_cols,
                "datetime_columns": datetime_cols,
            },
            storage_hint="session",
            suggested_name=filename.replace(".csv", "_data").replace("-", "_").replace(" ", "_"),
        )

    except pd.errors.EmptyDataError:
        return ToolResponse(
            payload=None,
            summary=f"Error: File '{filename}' is empty.",
            metadata={"error": "EmptyDataError", "filename": filename},
            storage_hint="never",
        )
    except pd.errors.ParserError as e:
        return ToolResponse(
            payload=None,
            summary=f"Error parsing '{filename}': {e}",
            metadata={"error": "ParserError", "filename": filename, "details": str(e)},
            storage_hint="never",
        )
