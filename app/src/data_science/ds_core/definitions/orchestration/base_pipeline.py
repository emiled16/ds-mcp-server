import json
import pickle
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import networkx as nx
import pandas as pd
from loguru import logger
from matplotlib import pyplot as plt
from pydantic import BaseModel, Field, model_validator
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.step import BaseStep


class BasePipeline(BaseModel):
    steps: dict[str, BaseStep] = Field(
        description="Dictionary of steps in the pipeline",
        default_factory=dict,
    )
    graph: nx.DiGraph = Field(
        description="Graph of the pipeline stored in the pipeline object",
        default_factory=nx.DiGraph,
    )
    active_graph: nx.DiGraph = Field(
        description=(
            "Graph of the pipeline used for execution(let's say we want to use only a subset of the pipeline). "
            "This is a copy of the graph stored in the pipeline object."
            "We can subset the active graph but it will always have the same input nodes."
        ),
        default_factory=nx.DiGraph,
    )
    input_nodes: set[str] = Field(
        description="Set of input nodes in the pipeline",
        default_factory=set,
    )
    mapping: dict[str, dict[str, str]] = Field(
        description="Mapping of input nodes to output nodes",
        default_factory=dict,
    )
    temp_dir: Optional[tempfile.TemporaryDirectory] = Field(
        description="Temporary directory for the pipeline",
        default=None,
    )

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="after")
    def init_temp_dir(self) -> None:
        """
        Initialize a temporary directory for the pipeline
        """
        self.temp_dir = tempfile.TemporaryDirectory()

    def __del__(self) -> None:
        """
        Delete the temporary directory when the pipeline is deleted
        """
        self.temp_dir.cleanup()

    def visualize(self, figsize: tuple[int, int] = (10, 6), active: bool = False) -> None:
        """
        Visualize the pipeline graph
        Args:
            figsize: Tuple of (width, height) for the plot
        """
        graph = self.active_graph if active else self.graph
        plt.figure(figsize=figsize)
        pos = nx.spring_layout(graph)

        # Draw input nodes in green
        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=[node for node in graph.nodes if node in self.input_nodes],
            node_color="lightgreen",
            node_size=2000,
        )
        # Draw output nodes in lightblue
        nx.draw_networkx_nodes(
            graph,
            pos,
            nodelist=[node for node in graph.nodes if "__output" in node],
            node_color="lightblue",
            node_size=2000,
        )
        # Draw edges
        nx.draw_networkx_edges(graph, pos, edge_color="gray", arrows=True, arrowsize=20)
        # Add labels
        nx.draw_networkx_labels(graph, pos)
        plt.title("Pipeline Graph")
        plt.axis("off")
        plt.tight_layout()
        plt.show()

    def sync_graphs(self) -> None:
        """
        Sync the active graph with the stored graph
        """
        self.active_graph = self.graph.copy()

    @property
    def number_of_steps(self) -> int:
        """
        Get the number of steps in the pipeline
        """
        return len(self.steps)

    def subset_graph(self, step_number: Optional[int] = None) -> None:
        """
        Subset the active graph to only include the specified nodes
        step_number is the number of steps to include in the active graph
        counting starts at 1 (excluding the input nodes)
        """
        number_of_input_nodes = len(self.input_nodes)
        if step_number is None:
            self.sync_graphs()
        elif (step_number < 0) or (step_number > self.number_of_steps):
            raise ValueError(f"Step number must be between 0 and {self.number_of_steps}")
        elif step_number == 0:
            self.active_graph = nx.DiGraph()
        else:
            self.active_graph = self.graph.subgraph(list(self.graph.nodes)[: step_number + number_of_input_nodes])

    def add_step(self, step: BaseStep, name: str, edges: Optional[dict[str, str]] = None) -> None:
        """
        Add a step to the pipeline with optional edge connections.

        Args:
            step: The BaseStep instance to add
            edges: Dictionary mapping step input parameter names to output nodes
        """

        edges = edges or {}

        # Add step to internal registry
        self.steps[name] = step

        # Add nodes for step inputs and output
        output_node = f"{name}__output"
        self.graph.add_node(output_node)

        # Process each parameter in the step's signature

        mapping = {}
        for step_input in step.inputs or []:
            input_node = f"{name}__{step_input.name}"

            if step_input.name in edges:
                # Connect to existing node
                self.graph.add_edge(edges[step_input.name], output_node)
                mapping[step_input.name] = edges[step_input.name]
            else:
                # Create input node
                self.graph.add_node(input_node)
                self.graph.add_edge(input_node, output_node)
                self.input_nodes.add(input_node)
                mapping[step_input.name] = input_node

        self.mapping[name] = mapping

        self.sync_graphs()

    def remove_step(self, name: str) -> None:
        """
        Remove a step from the pipeline
        Args:
            name: The name of the step to remove
        """
        if self.graph.has_node(f"{name}__output"):
            if self.graph.out_degree(f"{name}__output") == 0:
                self.graph.remove_node(f"{name}__output")
            else:
                logger.warning(f"Step {name} is not a leaf node, cannot remove")
        else:
            logger.warning(f"Step {name} not found in pipeline")

        self.sync_graphs()

    def _validate_graph(self) -> None:
        """Validate the pipeline graph structure."""
        if len(self.active_graph.nodes) == 0:
            return
        if not nx.is_directed_acyclic_graph(self.active_graph):
            raise ValueError("Pipeline graph must be acyclic")

        # Check for single output
        output_nodes = [node for node in self.active_graph.nodes if self.active_graph.out_degree(node) == 0]
        if len(output_nodes) != 1:
            raise ValueError("Pipeline must have exactly one output node")

    @classmethod
    def from_steps(
        cls,
        steps: list[tuple[BaseStep, str, dict[str, str]]] | list[tuple[BaseStep, str]] = [],
    ) -> "BasePipeline":
        """
        Create a pipeline from a list of steps
        Args:
            steps: List of tuples containing a step, the name of the step and optional edges. Example:
                [
                    (Step1, "step1", {"<input_node>": "<previous_step>__output"}),
                    (Step2, "step2", {"<input_node>": "<previous_step>__output"}),
                ]
        Returns:
            Pipeline: The created pipeline
        """
        complete_args_length = 3  # step, name, edges
        partial_args_length = 2  # step, name
        pipeline = cls()
        for step_edges in steps:
            if len(step_edges) == complete_args_length:
                step, name, edges = step_edges[0], step_edges[1], step_edges[2]
            elif len(step_edges) == partial_args_length:
                step, name = step_edges[0], step_edges[1]
                edges = {}
            else:
                raise ValueError("Invalid number of arguments for step")
            pipeline.add_step(step, name, edges)
        return pipeline

    def _execute(
        self,
        method: str,
        in_memory: bool = True,
        **inputs: Union[pd.DataFrame, SnowparkDataFrame],
    ) -> Union[pd.DataFrame, SnowparkDataFrame]:
        """
        Execute the pipeline using the specified method (fit or transform).

        Args:
            method: Either 'fit' or 'transform'
            inputs: Input DataFrames keyed by node names
            in_memory: Whether to store the results in memory
        """
        if len(self.active_graph.nodes) == 0:
            keys = list(inputs.keys())
            return inputs[keys[0]]
        self._validate_graph()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        temp_dir = Path(self.temp_dir.name) / f"{method}_{timestamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        # Validate inputs
        if set(inputs.keys()) != self.input_nodes:
            raise ValueError(f"Expected inputs: {self.input_nodes}, got: {set(inputs.keys())}")

        metadata = {
            "method": method,
            "inputs": [input for input in inputs.keys()],
            "in_memory": in_memory,
            "timestamp": timestamp,
        }

        with open(temp_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

        # Initialize results dictionary with inputs
        results = {}
        for input_node, input_data in inputs.items():
            if in_memory:
                results[input_node] = input_data
            else:
                input_data.to_parquet(temp_dir / f"{input_node}.parquet")

        # Process nodes in topological order
        for node in nx.topological_sort(self.active_graph):
            if node in inputs:  # Skip input nodes
                continue

            # Get step name from output node
            step_name = node.split("__")[0]
            step = self.steps[step_name]

            step_inputs = {}
            mapping = self.mapping[step_name]
            for key, value in mapping.items():
                if in_memory:
                    step_inputs[key] = results[value]
                else:
                    step_inputs[key] = pd.read_parquet(temp_dir / f"{value}.parquet")

            output = getattr(step, method)(**step_inputs)
            if in_memory:
                results[node] = output
            else:
                output.to_parquet(temp_dir / f"{node}.parquet")

        # Return final output
        if in_memory:
            return results[node]  # Last node in topological sort is output
        else:
            return pd.read_parquet(temp_dir / f"{node}.parquet")

    def save_pipeline(self, path: str) -> None:
        """
        Save the pipeline to a file
        Args:
            path: The path to save the pipeline
        """
        if not re.match(r"^.*\.pkl$", path):
            logger.error(f"Invalid path: {path}")
        # if path directory does not exist, create it
        directory = Path(path).parent
        directory.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "wb") as f:
                pickle.dump(self, f)
        except Exception as e:
            logger.error(f"Failed to save pipeline to {path}: {e}")
            raise e

    @classmethod
    def load_pipeline(cls, path: str) -> "BasePipeline":
        """
        Load the pipeline from a file
        Args:
            path: The path to load the pipeline
        Returns:
            Pipeline: The loaded pipeline
        """
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load pipeline from {path}: {e}")
            raise e

    def get_inputs(self) -> list[str]:
        """
        Get the input nodes of the pipeline
        Returns:
            List of input nodes
        """
        return list(self.input_nodes)

    def get_outputs(self) -> list[str]:
        """
        Get the outputs of the pipeline
        Returns:
            List of output nodes
        """
        return [node for node in self.active_graph.nodes if self.active_graph.out_degree(node) == 0]

    def get_all_outputs(self) -> list[str]:
        """
        Get all outputs of the pipeline including intermediate outputs
        Returns:
            List of all outputs
        """
        return [node for node in self.active_graph.nodes if "__output" in node]
