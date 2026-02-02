from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from src.data_science.snowflake.utils.yaml_utils import Yaml

# Cortex Analyst semantic model specification
# => https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/semantic-model-spec
#
# This is a re-implementation of the protobuf schema using Pydantic
# => https://github.com/Snowflake-Labs/semantic-model-generator/blob/main/semantic_model_generator/protos/semantic_model_pb2.pyi


AggregationType = Literal["aggregation_type_unknown", "sum", "avg", "median", "min", "max", "count", "count_distinct"]
ColumnKind = Literal["column_kind_unknown", "dimension", "measure", "time_dimension"]
JoinType = Literal["join_type_unknown", "inner", "left_outer"]
RelationshipType = Literal["relationship_type_unknown", "one_to_one", "many_to_one"]


class Dimension(BaseModel):
    name: str
    expr: str
    data_type: str

    synonyms: List[str] = Field(default_factory=list)
    description: str = ""
    unique: bool = False
    sample_values: List[str] = Field(default_factory=list)
    cortex_search_service_name: str = ""


class TimeDimension(BaseModel):
    name: str
    expr: str
    data_type: str

    synonyms: List[str] = Field(default_factory=list)
    description: str = ""
    unique: bool = False
    sample_values: List[str] = Field(default_factory=list)


class Measure(BaseModel):
    name: str
    expr: str
    data_type: str

    synonyms: List[str] = Field(default_factory=list)
    description: str = ""
    default_aggregation: AggregationType = "aggregation_type_unknown"
    sample_values: List[str] = Field(default_factory=list)


class NamedFilter(BaseModel):
    name: str
    expr: str

    synonyms: List[str] = Field(default_factory=list)
    description: str = ""


class FullyQualifiedTable(BaseModel):
    database: str
    schema_name: str = Field(alias="schema", serialization_alias="schema")
    table: str

    def table_path(self) -> str:
        return f"{self.database}.{self.schema_name}.{self.table}"


class PrimaryKey(BaseModel):
    columns: List[str] = Field(default_factory=list)


class Table(BaseModel):
    name: str
    base_table: FullyQualifiedTable

    synonyms: List[str] = Field(default_factory=list)
    description: str = ""
    dimensions: List[Dimension] = Field(default_factory=list)
    time_dimensions: List[TimeDimension] = Field(default_factory=list)
    measures: List[Measure] = Field(default_factory=list)
    primary_key: PrimaryKey = Field(default_factory=PrimaryKey)
    filters: List[NamedFilter] = Field(default_factory=list)

    def columns(self) -> List[Union[Dimension, Measure, TimeDimension, NamedFilter]]:
        return [*self.dimensions, *self.measures, *self.time_dimensions, *self.filters]


class RelationKey(BaseModel):
    left_column: str
    right_column: str


class Relationship(BaseModel):
    name: str
    left_table: str
    right_table: str
    relationship_columns: List[RelationKey]
    join_type: JoinType
    relationship_type: RelationshipType


StoredVerifiedQuery = str
"""SQL query without the logical table CTEs (cannot be executed)."""


# https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository
class VerifiedQuery(BaseModel):
    name: str
    question: str
    sql: StoredVerifiedQuery

    semantic_model_name: str = ""
    verified_at: Optional[int] = None
    verified_by: Optional[str] = None
    use_as_onboarding_question: bool = False


class VerifiedQueryRepository(BaseModel):
    verified_queries: List[VerifiedQuery]


# https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/semantic-model-spec#semantic-model
class CortexSemanticModel(BaseModel):
    name: str
    description: str = ""
    tables: List[Table] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    verified_queries: List[VerifiedQuery] = Field(default_factory=list)
    custom_instructions: str = ""

    @staticmethod
    def from_yaml(yaml_str: str) -> "CortexSemanticModel":
        return CortexSemanticModel.model_validate(Yaml.load_str(yaml_str))

    def to_yaml(self) -> str:
        return Yaml.dump_str(self.model_dump(mode="json", exclude_defaults=True, by_alias=True))
