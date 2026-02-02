from typing import Annotated, Union

from pydantic import Field

from src.data_science.regression.models.decision_tree import (
    DecisionTreeRegressorGridSearchConfig,
    DecisionTreeRegressorModel,
)
from src.data_science.regression.models.elastic_net import (
    ElasticNetRegressorGridSearchConfig,
    ElasticNetRegressorModel,
)
from src.data_science.regression.models.gradient_boosting import (
    GradientBoostingRegressorGridSearchConfig,
    GradientBoostingRegressorModel,
)
from src.data_science.regression.models.huber import (
    HuberRegressorGridSearchConfig,
    HuberRegressorModel,
)
from src.data_science.regression.models.lasso import (
    LassoRegressorGridSearchConfig,
    LassoRegressorModel,
)
from src.data_science.regression.models.linear_regression import (
    LinearRegressionRegressorGridSearchConfig,
    LinearRegressionRegressorModel,
)
from src.data_science.regression.models.neural_net import (
    NeuralNetworkRegressorGridSearchConfig,
    NeuralNetworkRegressorModel,
)
from src.data_science.regression.models.random_forest import (
    RandomForestRegressorGridSearchConfig,
    RandomForestRegressorModel,
)
from src.data_science.regression.models.xgboost import XGBRegressorGridSearchConfig, XGBRegressorModel

RegressorModel = Annotated[
    Union[
        LinearRegressionRegressorModel,
        LassoRegressorModel,
        ElasticNetRegressorModel,
        HuberRegressorModel,
        DecisionTreeRegressorModel,
        RandomForestRegressorModel,
        GradientBoostingRegressorModel,
        NeuralNetworkRegressorModel,
        XGBRegressorModel,
    ],
    Field(discriminator="model"),
]

RegressorGridSearchConfig = Annotated[
    Union[
        LinearRegressionRegressorGridSearchConfig,
        LassoRegressorGridSearchConfig,
        ElasticNetRegressorGridSearchConfig,
        HuberRegressorGridSearchConfig,
        DecisionTreeRegressorGridSearchConfig,
        RandomForestRegressorGridSearchConfig,
        GradientBoostingRegressorGridSearchConfig,
        NeuralNetworkRegressorGridSearchConfig,
        XGBRegressorGridSearchConfig,
    ],
    Field(discriminator="model"),
]
