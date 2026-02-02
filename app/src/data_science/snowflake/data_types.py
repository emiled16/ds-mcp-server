import json
from typing import Any, Literal, Optional, Sequence, Union, get_args

from src.data_science.snowflake.constants import SNOWFLAKE_VALUE_LIMIT_SIZE

# Values of the DATA_TYPE in INFORMATION_SCHEMA.COLUMNS:
# => https://docs.snowflake.com/en/sql-reference/info-schema/columns
VariantType = Literal["OBJECT", "ARRAY", "VARIANT"]
DatetimeType = Literal["DATE", "TIME", "TIMESTAMP", "TIMESTAMP_LTZ", "TIMESTAMP_NTZ"]
MainType = Literal["TEXT", "FLOAT", "NUMBER", "BOOLEAN"]
VARIANT_TYPES: Sequence[VariantType] = get_args(VariantType)

DataType = Union[MainType, DatetimeType, VariantType]
DATA_TYPES: Sequence[DataType] = [lit for typ in (MainType, DatetimeType, VariantType) for lit in get_args(typ)]


def serialize_variant(value: Any) -> Optional[str]:
    """Serialize the given value to be used in a Snowflake query."""
    if value is None:
        return None

    # Serialize objects as JSON
    if not isinstance(value, str):
        str_value = json.dumps(value, separators=(",", ":"), default=str, skipkeys=True)
    else:
        str_value = value

    if len(str_value) > SNOWFLAKE_VALUE_LIMIT_SIZE:
        raise ValueError(f"Variant value exceeds 16Mo: {str_value[:1000]}...")

    return str_value
