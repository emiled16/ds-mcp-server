import uuid
from typing import Any

from pydantic import BaseModel, Field

from src.data_science.feature_store.src.config import Config as FeatureStoreConfig
from src.data_science.features.base import AugmentedTransformationLibrary


class FeaturePipelineConfig(BaseModel):
    feature_store_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str
    feature_store: FeatureStoreConfig[AugmentedTransformationLibrary]  # type: ignore[valid-type]

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return super().model_dump(
            *args,
            **kwargs,
            exclude={
                "feature_store",  # FIXME: use below but handle skleanr objects
                # "feature_store": {
                #     "transformations": {
                #         "__all__": {  # For each transformation definition
                #             "inputs": {"__all__": {"type": True}},
                #             "outputs": {"__all__": {"type": True}},
                #         },
                #     },
                #     "steps": {
                #         "__all__": {  # For each step in the steps list
                #             "transformation": {
                #                 "inputs": {"__all__": {"type": True}},
                #                 "outputs": {"__all__": {"type": True}},
                #             },
                #         },
                #     },
                # },
            },
        )
