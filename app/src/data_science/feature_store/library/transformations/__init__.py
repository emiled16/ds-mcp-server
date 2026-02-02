from typing import Annotated, Union

from pydantic import Field

from src.data_science.feature_store.library.transformations.aggregation import Aggregation
from src.data_science.feature_store.library.transformations.cast_types import CastTypes
from src.data_science.feature_store.library.transformations.concat import Concat
from src.data_science.feature_store.library.transformations.cyclical_time_transform import (
    CyclicalTimeTransform,
)
from src.data_science.feature_store.library.transformations.drop_cols import DropCols
from src.data_science.feature_store.library.transformations.drop_cols_zero_var import (
    DropColsZeroVar,
)
from src.data_science.feature_store.library.transformations.drop_outliers_iqr import DropOutliersIQR
from src.data_science.feature_store.library.transformations.drop_rare_labels import DropRareLabels
from src.data_science.feature_store.library.transformations.drop_rows_duplicates import (
    DropRowsDuplicates,
)
from src.data_science.feature_store.library.transformations.drop_rows_na import DropRowsNA
from src.data_science.feature_store.library.transformations.drop_rows_out_of_bounds import (
    DropRowsOutOfBounds,
)
from src.data_science.feature_store.library.transformations.encode_one_hot import EncodeOneHot
from src.data_science.feature_store.library.transformations.feature_agglomeration import (
    FeatureAgglomeration,
)
from src.data_science.feature_store.library.transformations.fill_cols_values import FillColsValues
from src.data_science.feature_store.library.transformations.filter_rows import FilterRows
from src.data_science.feature_store.library.transformations.flatten_dict import FlattenDict
from src.data_science.feature_store.library.transformations.flatten_list import FlattenList
from src.data_science.feature_store.library.transformations.lag import Lag
from src.data_science.feature_store.library.transformations.maths_transform import MathsTransform
from src.data_science.feature_store.library.transformations.polynomial_features import (
    PolynomialFeatures,
)
from src.data_science.feature_store.library.transformations.reduction_pca import ReductionPCA
from src.data_science.feature_store.library.transformations.rename_columns import RenameColumns
from src.data_science.feature_store.library.transformations.scaling_numerical import (
    ScalingNumerical,
)
from src.data_science.feature_store.library.transformations.select_cols import SelectCols
from src.data_science.feature_store.library.transformations.sort import Sort
from src.data_science.feature_store.library.transformations.trunc_date import TruncDate

__all__ = [
    "Aggregation",
    "Lag",
    "SelectCols",
    "RenameColumns",
    "TruncDate",
    "Concat",
    "DropCols",
    "DropColsZeroVar",
    "DropOutliersIQR",
    "DropRowsOutOfBounds",
    "DropRareLabels",
    "DropRowsDuplicates",
    "DropRowsNA",
    "CastTypes",
    "FillColsValues",
    "MathsTransform",
    "PolynomialFeatures",
    "ReductionPCA",
    "ScalingNumerical",
    "FeatureAgglomeration",
    "EncodeOneHot",
    "Sort",
    "CyclicalTimeTransform",
    "FilterRows",
    "FlattenDict",
    "FlattenList",
    # "BasicCalendar",
]

TransformationLibrary = Annotated[
    Union[
        Aggregation,
        Lag,
        SelectCols,
        RenameColumns,
        TruncDate,
        Concat,
        DropCols,
        DropColsZeroVar,
        DropOutliersIQR,
        DropRowsOutOfBounds,
        DropRareLabels,
        DropRowsDuplicates,
        DropRowsNA,
        CastTypes,
        FillColsValues,
        MathsTransform,
        PolynomialFeatures,
        ReductionPCA,
        ScalingNumerical,
        FeatureAgglomeration,
        EncodeOneHot,
        Sort,
        CyclicalTimeTransform,
        FilterRows,
        FlattenDict,
        FlattenList,
        # BasicCalendar,
    ],
    Field(discriminator="name"),
]
