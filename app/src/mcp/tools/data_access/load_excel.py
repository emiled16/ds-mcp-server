"""Load Excel file tool."""

import pandas as pd

from src.constants import DATASET_PATH
from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse


@mcp.tool
@process_tool
@register_tool
async def load_excel(
    filename: str,
    sheet_name: str | int = 0,
    nrows: int | None = None,
) -> str:
    """Load an Excel file from the datasets folder.

    Loads an Excel file (xlsx, xls) and returns a summary with shape, column names, and memory usage.

    Args:
        filename: Name of the Excel file (e.g., 'data.xlsx')
        sheet_name: Sheet name or index to load (default: first sheet)
        nrows: Optional number of rows to load

    Returns:
        ToolResponse with DataFrame in payload and summary statistics

    Example:
        "Load the data.xlsx file"
        → load_excel(filename="data.xlsx")

        "Load the 'Sales' sheet from report.xlsx"
        → load_excel(filename="report.xlsx", sheet_name="Sales")
    """
    file_path = DATASET_PATH / filename

    if not file_path.exists():
        return ToolResponse(
            payload=None,
            summary=f"Error: File '{filename}' not found in datasets folder.",
            metadata={"error": "FileNotFoundError", "filename": filename},
            storage_hint="never",
        )

    try:
        # Load Excel
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=nrows)

        # Get sheet names for metadata
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names

        # Generate column type summary
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        # Memory usage
        memory_mb = df.memory_usage(deep=True).sum() / 1024**2

        # Create column list (truncate if too many)
        max_cols_display = 15
        col_display = df.columns.tolist()
        if len(col_display) > max_cols_display:
            col_display = col_display[:max_cols_display] + [f"... +{len(df.columns) - max_cols_display} more"]

        # Generate summary
        loaded_sheet = sheet_name if isinstance(sheet_name, str) else sheet_names[sheet_name]
        summary = (
            f"Loaded '{filename}' (sheet: '{loaded_sheet}') successfully:\n"
            f"  • Rows: {len(df):,}" + (f" (limited to {nrows})" if nrows else "") + "\n"
            f"  • Columns: {len(df.columns)}\n"
            f"  • Column names: {', '.join(col_display)}\n"
            f"  • Available sheets: {', '.join(sheet_names)}\n"
            f"  • Column types: {len(numeric_cols)} numeric, {len(categorical_cols)} categorical\n"
            f"  • Memory usage: {memory_mb:.2f} MB"
        )

        # Add preview
        preview = df.head(3).to_string(max_cols=10, max_colwidth=30)
        summary += f"\n\nPreview (first 3 rows):\n{preview}"

        return ToolResponse(
            payload=df,
            summary=summary,
            metadata={
                "filename": filename,
                "sheet_name": loaded_sheet,
                "available_sheets": sheet_names,
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "memory_mb": memory_mb,
            },
            storage_hint="session",
            suggested_name=f"{filename.split('.')[0]}_{loaded_sheet}_data".replace("-", "_").replace(" ", "_"),
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error loading '{filename}': {e}",
            metadata={"error": type(e).__name__, "filename": filename, "details": str(e)},
            storage_hint="never",
        )
