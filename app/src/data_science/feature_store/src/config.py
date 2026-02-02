from typing import Annotated, Any, Generic, Optional, TypeVar, Union, get_args

from pydantic import BaseModel, Field, model_validator

from src.data_science.ds_core.definitions.orchestration.pipeline import Pipeline
from src.data_science.feature_store.library.transformations import TransformationLibrary

# TypeVar allows projects to specify their custom transformation library type
T = TypeVar("T", bound=TransformationLibrary)


def create_augmented_transformation_library(*additional_transformations):
    original_types = list(get_args(get_args(TransformationLibrary)[0]))

    all_types = original_types + list(additional_transformations)

    return Annotated[Union[tuple(all_types)], Field(discriminator="name")]


class ParsingStep(BaseModel, Generic[T]):
    model_config = {"arbitrary_types_allowed": True}

    name: str
    transformation: Union[T, str]
    inputs: Optional[dict[str, str]] = Field(default=None)

    def model_dump(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "transformation": self.transformation.model_dump(),
            "inputs": self.inputs,
        }


class Config(BaseModel, Generic[T]):
    transformations: dict[str, T] = Field(default_factory=dict)
    steps: list[ParsingStep[T]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_steps(self):
        for step in self.steps:
            if isinstance(step.transformation, str):
                if step.transformation not in self.transformations:
                    raise ValueError(f"Transformation {step.transformation} not found")
                step.transformation = self.transformations[step.transformation]
        return self

    def generate_pipeline(self) -> Pipeline:
        pipeline = Pipeline()
        for step in self.steps:
            if isinstance(step.transformation, str):
                raise ValueError("Transformation must be a class")
            pipeline.add_step(step.transformation, step.name, step.inputs)
        return pipeline
