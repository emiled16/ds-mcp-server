from abc import ABC

from pydantic import BaseModel, ConfigDict, Field

from src.data_science.ds_core.definitions.orchestration.io import BaseInput, BaseOutput, BaseParameter


class BaseStep(BaseModel, ABC):
    name: str = Field(description="Name of the step")
    description: str = Field(description="Description of the step")
    inputs: list[BaseInput] | None = Field(default=None)
    outputs: list[BaseOutput] | None = Field(default=None)
    parameters: list[BaseParameter] | None = Field(default=None)
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def validate_inputs(self, **kwargs) -> bool:
        # - validate that all required inputs are present, with correct types
        # - flag any additional inputs that are present but not required
        errors = {}
        for required_input in self.inputs or []:
            if required_input.name not in kwargs:
                errors[required_input.name] = f"Missing input of type {required_input.type}"
            elif not isinstance(kwargs[required_input.name], required_input.type):
                errors[required_input.name] = f"Incorrect type, should be {required_input.type}"
        if errors:
            raise ValueError(errors)
        return True
