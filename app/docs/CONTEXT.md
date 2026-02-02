# Project Context

## Overview

This project is an MCP (Model Context Protocol) server that provides data science capabilities to an AI agent through a structured, three-layer architecture.

## Architecture

The MCP server consists of three layers:

- **Layer 1: Data Science Tools** - MCP tools that expose data science functionality
- **Layer 2: Middleware** - Processes input and output of tools, handles tool responses
- **Layer 3: Infrastructure** - Contains MLflow tracking server, databases (MongoDB and Postgres), object storage (MinIO), and can be extended with Celery and Redis as needed

## Problem Statement

A significant limitation with LLMs is the context window constraint. Providing tools that return entire datasets is not feasible due to token limits.

## Solution Approach

To solve this issue, we use a concept of **variables** (implemented as `tool_response` in the repository). Every time a tool is called, it stores the result in a `tool_response` variable. The tool response acts like a variable that the agent can reference in subsequent tool calls. The agent never sees the entire dataset, only a summary of the tool response.

### Tool Response Structure

```json
{
  "payload": "<CAN BE ANYTHING or EVEN NONE>",
  "summary": "the summary of the tool response",
  "metadata": {
    "tool_name": "the name of the tool that was called",
    "tool_args": "the arguments that were passed to the tool",
    "tool_kwargs": "the keyword arguments that were passed to the tool",
    "tool_return_type": "the return type of the tool",
    "tool_return_value": "the return value of the tool"
  },
  "storage_hint": "always|never|auto",
  "suggested_name": "the suggested name of the tool response",
  "entity_id": "the entity id of the tool response",
  "version": 1,
  "type": "tool_response",
  "created_at": "the creation time of the tool response",
  "updated_at": "the last update time of the tool response"
}
```

### Key Concepts

- **summary**: What the agent sees and uses to understand the tool response
- **payload**: Contains the actual data/variables that can be manipulated and used in subsequent tool calls
- **entity_id**: A unique identifier for the tool response (acts as a variable name)
- **metadata**: Internal information about the tool execution
- **storage_hint**: Indicates whether to store the tool response ("always", "never", or "auto")

### Middleware Processing

When an agent calls a tool, the middleware processes the tool response:

- Verifies if the query is cached or exists in saved data to avoid duplicate calls
- Stores the tool response in the database or object storage if `storage_hint` is "always"
- Returns only the summary of the tool response to the agent

## Storage System

We use a combination of document store and object store to store tool responses:

- **Document Store**: Stores the entire tool response except the payload if it's too large
- **Object Store**: Stores the payload of the tool response or any other artifacts that are too large for the document store

## Workflow

When an agent is asked to perform a task, it follows this workflow:

1. **Assess the task**: Verify requirements and identify what is missing to solve the task
2. **Create a plan**: Develop a solution plan that typically includes:
   - Use data tools to explore the data and understand the dataset, possible features, etc. (every call is stored in a tool response variable)
   - Once the dataset is well understood, create a config for the pipeline (a pipeline consists of a feature store and a model hyperparameter tuning experiment)
   - Use a tool to validate the config
   - Once validated, submit the pipeline to a running job. Jobs are managed by Celery and assigned to workers. Jobs are logged in MLflow and pipelines are saved through MLflow
   - Wait until jobs are completed, then evaluate and analyze results to come up with a final solution

## Pipelines

Feature stores and models can each be considered as pipelines. A pipeline in our system is built on top of MLflow's `pyfunc` model. It orchestrates the data science pipeline and handles the data science workflow. This allows us to deploy pipelines or schedule them to run periodically with monitoring and alerts.

## Notetaking

The agent needs to keep track of the problem statement, findings, results, analysis, etc. This is where notetaking comes in. The agent should have access to a tool that can update and append to a note-taking document. This document should be stored in the database and can be accessed by the agent to refer to past findings, results, and analysis.

## Data Science Tools

We can use functionalities in `src/data_science` to create tools that can be used by the agent. This is an entire project that was used for a forecasting data science project. We can reuse the same tools and functionalities to create MCP tools for the agent.

## Future Vision

In the future, the backend could be connected to a frontend where users have access to a platform to perform data science experiments through a UI. This would provide an alternative interface to the AI agent, allowing users to:

- Interact with the same data science tools through a graphical interface
- Visualize experiments, results, and pipelines
- Manage and monitor data science workflows
- Collaborate on experiments and share results

The backend architecture is designed to support both AI agent interactions (via MCP) and potential future frontend integrations, ensuring the same underlying tools and infrastructure can serve multiple interfaces.
