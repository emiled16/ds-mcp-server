#!/bin/bash
# Start the MCP server

set -e

cd "$(dirname "$0")/.."

echo "Starting MCP server..."
python -m src.mcp.server

