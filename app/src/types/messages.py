"""Shared type definitions for agent package."""

from typing import Literal

from langchain.messages import AIMessage, HumanMessage, SystemMessage

# Message types
Message = HumanMessage | SystemMessage | AIMessage

# MCP types
MCPType = Literal["streamable_http"]

EntityType = Literal["tool_response", "job", "note"]
