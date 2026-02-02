"""Feature Pipeline implementation with MLflow PyFunc support.

This module provides a reusable, versioned feature pipeline that can:
- Chain multiple transformations together
- Fit and transform data (sklearn-like API)
- Be saved to MLflow as a model artifact
- Be loaded and used for inference
"""

import pickle
from typing import Any

import mlflow
import pandas as pd
from loguru import logger

# Import available transformations
from src.data_science.feature_store.library.transformations import (
    Aggregation,
    CastTypes,
    CyclicalTimeTransform,
    DropCols,
    DropColsZeroVar,
    DropOutliersIQR,
    DropRareLabels,
    DropRowsDuplicates,
    DropRowsNA,
    DropRowsOutOfBounds,
    EncodeOneHot,
    FeatureAgglomeration,
    FillColsValues,
    FilterRows,
    Lag,
    MathsTransform,
    PolynomialFeatures,
    ReductionPCA,
    RenameColumns,
    ScalingNumerical,
    SelectCols,
    Sort,
)

# Registry of available transformations
TRANSFORMATION_REGISTRY = {
    "Lag": Lag,
    "Aggregation": Aggregation,
    "SelectCols": SelectCols,
    "DropCols": DropCols,
    "RenameColumns": RenameColumns,
    "FillColsValues": FillColsValues,
    "DropRowsNA": DropRowsNA,
    "DropRowsDuplicates": DropRowsDuplicates,
    "FilterRows": FilterRows,
    "ScalingNumerical": ScalingNumerical,
    "EncodeOneHot": EncodeOneHot,
    "CyclicalTimeTransform": CyclicalTimeTransform,
    "MathsTransform": MathsTransform,
    "PolynomialFeatures": PolynomialFeatures,
    "Sort": Sort,
    "CastTypes": CastTypes,
    "DropColsZeroVar": DropColsZeroVar,
    "DropOutliersIQR": DropOutliersIQR,
    "DropRareLabels": DropRareLabels,
    "DropRowsOutOfBounds": DropRowsOutOfBounds,
    "FeatureAgglomeration": FeatureAgglomeration,
    "ReductionPCA": ReductionPCA,
}


class FeaturePipeline(mlflow.pyfunc.PythonModel):
    """Feature engineering pipeline that chains transformations.

    This class implements both a sklearn-like API (fit/transform) and
    MLflow's PyFunc model interface for serving.

    Attributes:
        steps: List of transformation configurations
        transformations: Fitted transformation instances
        is_fitted: Whether the pipeline has been fitted
    """

    def __init__(self, steps: list[dict] | None = None):
        """Initialize feature pipeline.

        Args:
            steps: List of transformation configurations, each with:
                {
                    "name": "TransformationName",
                    "parameters": {...}
                }
        """
        self.steps = steps or []
        self.transformations = []
        self.is_fitted = False
        self._metadata = {
            "total_steps": len(self.steps),
            "step_names": [s.get("name") for s in self.steps],
        }

    def fit(self, df: pd.DataFrame) -> "FeaturePipeline":
        """Fit the pipeline on training data.

        Args:
            df: Input DataFrame

        Returns:
            Self for method chaining
        """
        logger.info(f"Fitting feature pipeline with {len(self.steps)} steps")

        self.transformations = []
        current_df = df.copy()

        for i, step_config in enumerate(self.steps):
            step_name = step_config.get("name")
            step_params = step_config.get("parameters", {})

            logger.info(f"Step {i+1}/{len(self.steps)}: Fitting {step_name}")

            # Create transformation instance
            transform_class = TRANSFORMATION_REGISTRY.get(step_name)
            if not transform_class:
                raise ValueError(f"Unknown transformation: {step_name}")

            try:
                # Build parameters
                param_class = transform_class.model_fields.get("parameters")
                if param_class and step_params:
                    param_type = param_class.annotation
                    params = param_type(**step_params)
                    transform = transform_class(parameters=params)
                else:
                    transform = transform_class(**step_params)

                # Fit and transform
                current_df = transform.fit_transform(df=current_df)
                self.transformations.append(transform)

                logger.info(
                    f"  Result shape: {current_df.shape[0]:,} rows × {current_df.shape[1]} columns"
                )

            except Exception as e:
                logger.exception(f"Error in step {i+1} ({step_name}): {e}")
                raise

        self.is_fitted = True
        logger.info("Pipeline fitting complete")
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform data using fitted pipeline.

        Args:
            df: Input DataFrame

        Returns:
            Transformed DataFrame
        """
        if not self.is_fitted:
            raise ValueError("Pipeline not fitted. Call fit() or fit_transform() first.")

        logger.info(f"Transforming data through {len(self.transformations)} steps")

        current_df = df.copy()
        for i, transform in enumerate(self.transformations):
            step_name = self.steps[i].get("name")
            logger.debug(f"Step {i+1}/{len(self.transformations)}: Applying {step_name}")
            current_df = transform.transform(df=current_df)

        logger.info(f"Transformation complete: {current_df.shape[0]:,} rows × {current_df.shape[1]} columns")
        return current_df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step.

        Args:
            df: Input DataFrame

        Returns:
            Transformed DataFrame
        """
        self.fit(df)
        return self.transform(df)

    def predict(self, context: Any, model_input: pd.DataFrame) -> pd.DataFrame:
        """MLflow PyFunc predict method.

        This method is called when the pipeline is loaded as an MLflow model
        and used for inference.

        Args:
            context: MLflow context (unused)
            model_input: Input DataFrame

        Returns:
            Transformed DataFrame
        """
        return self.transform(model_input)

    def save(self, path: str) -> None:
        """Save pipeline to disk using pickle.

        Args:
            path: File path to save to
        """
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"Saved pipeline to {path}")

    @classmethod
    def load(cls, path: str) -> "FeaturePipeline":
        """Load pipeline from disk.

        Args:
            path: File path to load from

        Returns:
            Loaded FeaturePipeline instance
        """
        with open(path, "rb") as f:
            pipeline = pickle.load(f)
        logger.info(f"Loaded pipeline from {path}")
        return pipeline

    def get_metadata(self) -> dict:
        """Get pipeline metadata.

        Returns:
            Dictionary with pipeline information
        """
        return {
            **self._metadata,
            "is_fitted": self.is_fitted,
            "steps": self.steps,
        }

    def __repr__(self) -> str:
        """String representation of pipeline."""
        status = "fitted" if self.is_fitted else "not fitted"
        return f"FeaturePipeline(steps={len(self.steps)}, {status})"


def create_feature_pipeline_from_config(config: dict) -> FeaturePipeline:
    """Create a FeaturePipeline from a configuration dictionary.

    Args:
        config: Configuration with "steps" list

    Returns:
        Initialized FeaturePipeline
    """
    steps = config.get("steps", [])
    return FeaturePipeline(steps=steps)
