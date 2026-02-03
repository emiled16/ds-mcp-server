from src.data_science.feature_store.src.config import create_augmented_transformation_library
from src.data_science.features.merge import Merge
from src.data_science.features.ordinal_encoder import OrdinalEncoder
from src.data_science.features.timeseries_add_missing_dates import AddMissingDates
from src.data_science.features.timeseries_age import TimeSeriesAge
from src.data_science.features.timeseries_calendar_advanced import AdvancedCalendar
from src.data_science.features.timeseries_cumulative_monthly_sum import CumulativeMonthlySum
from src.data_science.features.timeseries_custom_filter import CustomFilter
from src.data_science.features.timeseries_dim_calendar import TimeSeriesDimCalendar
from src.data_science.features.timeseries_frequency import TimeSeriesFrequency
from src.data_science.features.timeseries_previous_month_aggregation import PreviousMonthAggregation
from src.data_science.features.timeseries_recency import TimeSeriesRecency
from src.data_science.features.timeseries_remove_early_zeros import TimeSeriesRemoveEarlyZeros
from src.data_science.features.timeseries_rolling_features import RollingFeatures
from src.data_science.features.timeseries_segmentation_filtering import TimeSeriesSegmemtationFiltering

AugmentedTransformationLibrary = create_augmented_transformation_library(
    AddMissingDates,
    RollingFeatures,
    TimeSeriesAge,
    TimeSeriesRecency,
    AdvancedCalendar,
    CustomFilter,
    Merge,
    OrdinalEncoder,
    CumulativeMonthlySum,
    TimeSeriesFrequency,
    PreviousMonthAggregation,
    TimeSeriesRemoveEarlyZeros,
    TimeSeriesSegmemtationFiltering,
    TimeSeriesDimCalendar,
)
