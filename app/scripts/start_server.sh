#!/bin/bash
# Start the MCP server

set -e

cd "$(dirname "$0")/.."

# Use project .venv if present
if [ -d ".venv" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python"
fi

echo "Starting MCP server..."
exec "$PYTHON" -m src.mcp.server

