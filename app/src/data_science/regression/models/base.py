from typing import Any, Callable, Iterable, Literal, Optional, Union

from optuna import Trial
from pydantic import BaseModel, ConfigDict
from snowflake.ml.modeling.ensemble.gradient_boosting_regressor import (
    GradientBoostingRegressor,
)
from snowflake.ml.modeling.ensemble.random_forest_regressor import RandomForestRegressor
from snowflake.ml.modeling.linear_model.elastic_net import ElasticNet
from snowflake.ml.modeling.linear_model.huber_regressor import HuberRegressor
from snowflake.ml.modeling.linear_model.lasso import Lasso
from snowflake.ml.modeling.linear_model.linear_regression import LinearRegression
from snowflake.ml.modeling.neural_network.mlp_regressor import MLPRegressor
from snowflake.ml.modeling.tree.decision_tree_regressor import DecisionTreeRegressor

SnowflakeModelClassType = Union[
    GradientBoostingRegressor,
    RandomForestRegressor,
    LinearRegression,
    Lasso,
    ElasticNet,
    HuberRegressor,
    DecisionTreeRegressor,
    MLPRegressor,
]


class BaseRegressionModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        # Disable protected namespace checking (needed for model_class since model_ is protected)
        protected_namespaces=(),
    )
    model: Literal[
        "GradientBoostingRegressor",
        "RandomForestRegressor",
        "LinearRegressionRegressor",
        "LassoRegressor",
        "ElasticNetRegressor",
        "HuberRegressor",
        "DecisionTreeRegressor",
        "NeuralNetworkRegressor",
    ]
    model_class: type[SnowflakeModelClassType]

    def get_model(
        self,
        input_cols: Optional[Union[str, Iterable[str]]] = None,
        output_cols: Optional[Union[str, Iterable[str]]] = None,
        target_cols: Optional[Union[str, Iterable[str]]] = None,
        passthrough_cols: Optional[Union[str, Iterable[str]]] = None,
    ) -> SnowflakeModelClassType:
        # create a class from base model
        return self.model_class(
            input_cols=input_cols,
            output_cols=output_cols,
            label_cols=target_cols,
            passthrough_cols=passthrough_cols,
            **self.model_dump(exclude={"model", "model_class"}),
        )


class BaseRegressionModelGridSearchConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    model: Literal[
        "GradientBoostingRegressor",
        "RandomForestRegressor",
        "LinearRegressionRegressor",
        "LassoRegressor",
        "ElasticNetRegressor",
        "HuberRegressor",
        "DecisionTreeRegressor",
        "NeuralNetworkRegressor",
    ]

    def get_optuna_grid_search_callable(self) -> Callable[[Trial], dict[str, Any]]:
        def suggest_config(trial: Trial) -> dict[str, Any]:
            d = {
                k: trial.suggest_categorical(k, v)
                for k, v in self.model_dump(exclude={"model"}).items()
                if v is not None
            }
            d["model"] = self.model
            return d

        return suggest_config
