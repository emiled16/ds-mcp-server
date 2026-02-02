"""Meta tools for tool discovery and documentation."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import get_all_tools, get_tool_function, list_tool_names, register_tool
from src.models.tool_response import ToolResponse


@mcp.tool
@process_tool
@register_tool
def tool_description(func_name: str) -> str:
    """Get the description/docstring of a tool.

    Returns the full docstring of a registered tool function,
    including arguments and examples.

    Args:
        func_name: Name of the tool function

    Returns:
        ToolResponse with tool documentation

    Example:
        "What does load_csv do?"
        → tool_description(func_name="load_csv")
    """
    tool = get_tool_function(func_name)

    if not tool:
        return ToolResponse(
            payload=None,
            summary=f"Tool '{func_name}' not found. Use list_available_tools() to see all tools.",
            metadata={"error": "NotFound", "func_name": func_name},
            storage_hint="never",
        )

    description = tool.__doc__ or "No documentation available."

    return ToolResponse(
        payload={"func_name": func_name, "docstring": description},
        summary=f"## {func_name}\n\n{description}",
        metadata={"func_name": func_name},
        storage_hint="never",
    )


@mcp.tool
@process_tool
@register_tool
def list_available_tools(category: str | None = None) -> str:
    """List all available MCP tools.

    Shows all registered tools organized by category.

    Args:
        category: Optional category filter ('data', 'exploration', 'jobs', 'notes', 'meta')

    Returns:
        ToolResponse with list of tools

    Example:
        "What tools are available?"
        → list_available_tools()

        "Show data exploration tools"
        → list_available_tools(category="exploration")
    """
    tools = get_all_tools()

    # Categorize tools
    categories = {
        "data": ["list_available_datasets", "load_csv", "load_excel", "load_dataset"],
        "exploration": ["describe_dataset", "profile_data", "analyze_correlations", "detect_missing_values"],
        "transformation": ["list_available_transformations", "apply_transformation"],
        "jobs": ["submit_training_job", "get_job_status", "get_job_result", "cancel_job", "list_jobs"],
        "notes": ["create_note", "update_note", "append_to_note", "get_note", "search_notes", "list_notes"],
        "meta": ["tool_description", "list_available_tools", "list_stored_entities"],
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
        filtered_tools = {k: v for k, v in tools.items() if k in categories[category]}
    else:
        filtered_tools = tools

    # Build summary
    summary = "# Available MCP Tools\n\n"

    for cat_name, cat_tools in categories.items():
        if category and cat_name != category:
            continue

        cat_display = cat_name.replace("_", " ").title()
        available = [t for t in cat_tools if t in filtered_tools]

        if available:
            summary += f"## {cat_display} ({len(available)} tools)\n"
            for tool_name in available:
                tool = filtered_tools.get(tool_name)
                if tool and tool.__doc__:
                    # Get first line of docstring
                    first_line = tool.__doc__.strip().split("\n")[0]
                    summary += f"• **{tool_name}**: {first_line}\n"
                else:
                    summary += f"• **{tool_name}**\n"
            summary += "\n"

    # Add uncategorized tools
    all_categorized = set()
    for cat_tools in categories.values():
        all_categorized.update(cat_tools)

    uncategorized = [t for t in filtered_tools if t not in all_categorized]
    if uncategorized and not category:
        summary += "## Other Tools\n"
        for tool_name in uncategorized:
            summary += f"• **{tool_name}**\n"
        summary += "\n"

    summary += f"\nTotal tools: {len(filtered_tools)}\n"
    summary += "\nUse tool_description(func_name='...') to get detailed documentation."

    return ToolResponse(
        payload={
            "tools": list(filtered_tools.keys()),
            "categories": {k: [t for t in v if t in filtered_tools] for k, v in categories.items()},
            "total": len(filtered_tools),
        },
        summary=summary,
        metadata={"category": category, "total": len(filtered_tools)},
        storage_hint="never",
    )
