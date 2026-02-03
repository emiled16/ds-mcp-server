"""
Optional Snowflake support. All snowflake.* imports are guarded here.
When the 'snowflake' extra is not installed, SNOWFLAKE_AVAILABLE is False
and other exports are None. Use require_snowflake() at entry points that need Snowflake.

Install with: pip install .[snowflake]
"""

from __future__ import annotations

from typing import Any

SNOWFLAKE_AVAILABLE = False
Session: Any = None
SnowparkDataFrame: Any = None
get_active_session: Any = None
snowpark: Any = None
snowpark_functions: Any = None
Window: Any = None
Registry: Any = None
ModelSignature: Any = None
snowpark_metrics_regression: Any = None
SnowparkSessionException: Any = None
OBJECT: Any = None
col: Any = None
count: Any = None
lit: Any = None
lower: Any = None
# snowpark.types
DataType: Any = None
BooleanType: Any = None
ByteType: Any = None
FloatType: Any = None
IntegerType: Any = None
PandasDataFrameType: Any = None
PandasSeriesType: Any = None
StringType: Any = None

try:
    import snowflake.snowpark.functions as _snowpark_functions
    from snowflake import snowpark as _snowpark
    from snowflake.snowpark import DataFrame as _SnowparkDataFrame
    from snowflake.snowpark import Session as _Session
    from snowflake.snowpark import Window as _Window
    from snowflake.snowpark import context as _context
    from snowflake.snowpark.exceptions import SnowparkSessionException as _SnowparkSessionException
    from snowflake.snowpark.functions import col as _col
    from snowflake.snowpark.functions import count as _count
    from snowflake.snowpark.functions import lit as _lit
    from snowflake.snowpark.functions import lower as _lower

    Session = _Session
    SnowparkDataFrame = _SnowparkDataFrame
    Window = _Window
    get_active_session = _context.get_active_session
    snowpark = _snowpark
    snowpark_functions = _snowpark_functions
    col, count, lit, lower = _col, _count, _lit, _lower
    SnowparkSessionException = _SnowparkSessionException

    from snowflake.snowpark.types import (
        BooleanType as _BooleanType,
    )
    from snowflake.snowpark.types import (
        ByteType as _ByteType,
    )
    from snowflake.snowpark.types import (
        DataType as _DataType,
    )
    from snowflake.snowpark.types import (
        FloatType as _FloatType,
    )
    from snowflake.snowpark.types import (
        IntegerType as _IntegerType,
    )
    from snowflake.snowpark.types import (
        PandasDataFrameType as _PandasDataFrameType,
    )
    from snowflake.snowpark.types import (
        PandasSeriesType as _PandasSeriesType,
    )
    from snowflake.snowpark.types import (
        StringType as _StringType,
    )

    DataType = _DataType
    BooleanType = _BooleanType
    ByteType = _ByteType
    FloatType = _FloatType
    IntegerType = _IntegerType
    PandasDataFrameType = _PandasDataFrameType
    PandasSeriesType = _PandasSeriesType
    StringType = _StringType

    try:
        import snowflake.ml.modeling.metrics.regression as _snowpark_metrics_regression
        from snowflake.ml.model.model_signature import ModelSignature as _ModelSignature
        from snowflake.ml.registry import Registry as _Registry

        Registry = _Registry
        ModelSignature = _ModelSignature
        snowpark_metrics_regression = _snowpark_metrics_regression
    except ImportError:
        pass

    try:
        from snowflake.sqlalchemy import OBJECT as _OBJECT

        OBJECT = _OBJECT
    except ImportError:
        pass

    SNOWFLAKE_AVAILABLE = True
except ImportError:
    pass

# Alias used by many call sites
F = snowpark_functions

# Convenience exports from snowpark.functions (None when not available)
col: Any = None
count: Any = None
lit: Any = None
lower: Any = None

# Fallback for Column(OBJECT) when snowflake is not installed (e.g. dim_runs, etc.)
if not SNOWFLAKE_AVAILABLE and OBJECT is None:
    try:
        from sqlalchemy import Text

        OBJECT = Text  # placeholder so table definitions can load
    except ImportError:
        pass


def require_snowflake() -> None:
    """Raise ImportError with install hint if the snowflake extra is not installed."""
    if not SNOWFLAKE_AVAILABLE:
        raise ImportError(
            "Snowflake support requires the 'snowflake' extra. Install with: pip install .[snowflake]"
        ) from None
