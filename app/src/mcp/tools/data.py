from pathlib import Path
from typing import Any

from src.constants import DATASET_PATH
from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


def dataset_info(ds: Path) -> dict[str, Any]:
    return {
        "name": ds.name,
        "size_mb": round(ds.stat().st_size / (1024 * 1024), 2),
        "path": str(ds),
    }


@mcp.tool
@process_tool
@register_tool
async def list_available_datasets() -> str:
    """List all available datasets in the datasets folder.

    Returns:
        JSON string with ToolResponse format containing list of dataset filenames

    Example:
        "List all datasets I can use"
        → list_available_datasets()
    """
    datasets = list(DATASET_PATH.glob("*.csv"))

    if not datasets:
        response = {
            "payload": [],
            "summary": "No datasets found in the datasets folder.",
            "metadata": {"count": 0, "path": str(DATASET_PATH)},
            "storage_hint": "never",
        }
        return ToolResponse.from_dict(response)

    dataset_list = [dataset_info(ds) for ds in datasets]

    response = {
        "payload": dataset_list,
        "summary": f"Available datasets ({len(dataset_list)}):\n"
        + "\n".join(
            f"  - {info['name']}" + (f" ({info['size_mb']} MB)" if info["size_mb"] else "") for info in dataset_list
        ),
        "metadata": {"count": len(dataset_list), "path": str(DATASET_PATH)},
        "storage_hint": "never",
    }

    tool_response = ToolResponse.from_dict(response)
    await get_repository_registry().save(tool_response)

    return tool_response
