"""Shared MCP instance to avoid circular imports."""

from fastmcp import FastMCP

# Single source of truth for the MCP instance
mcp = FastMCP("DataScienceToolbox")
