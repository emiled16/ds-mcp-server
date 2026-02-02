# see docs here: https://docs.snowflake.com/en/developer-guide/snowflake-ml/model-registry/model-management

from typing import Optional

import pandas as pd
from snowflake.snowpark import Session


def set_schema(session: Session, schema_name: str) -> None:
    session.sql(f"USE SCHEMA {schema_name}").collect()


def list_models(
    session: Session,
    model_name: str,
    database_name: str,
    schema_name: Optional[str] = None,
) -> pd.DataFrame:
    schema_condition = f"AND schema_name = '{schema_name}'" if schema_name else ""
    query = f"""
    SELECT
        catalog_name,
        schema_name,
        model_name,
        model_version_name,
        version_aliases,
        metadata:metric AS metrics,
        comment,
        owner,
        functions,
        created_on,
        last_altered_on
    FROM {database_name}.INFORMATION_SCHEMA.MODEL_VERSIONS
    WHERE model_name = '{model_name}'
    {schema_condition}
    ORDER BY created_on, last_altered_on;
    """
    return session.sql(query).to_pandas()


def model_version_by_alias(
    session: Session,
    model_name: str,
    alias: str,
    database_name: str,
    schema_name: str,
) -> Optional[str]:
    set_schema(session, schema_name)
    models = list_models(session, model_name, database_name, schema_name)
    result = models.query(f"VERSION_ALIASES == '{alias}'")["MODEL_VERSION_NAME"].values
    if len(result) == 0:
        return None
    return result[0]


def model_alias_by_version(
    session: Session,
    model_name: str,
    version_name: str,
    database_name: str,
    schema_name: str,
) -> Optional[str]:
    set_schema(session, schema_name)
    models = list_models(session, model_name, database_name, schema_name)
    result = models.query(f"MODEL_VERSION_NAME == '{version_name}'")["VERSION_ALIASES"].values
    if len(result) == 0:
        return None
    return result[0]


def promote_model_version(
    session: Session,
    model_name: str,
    version_name: str,
    database_name: str,
    schema_name: str,
    alias: str = "PROD",
) -> None:
    set_schema(session, schema_name)
    # remove needed alias from version if exists
    current_version = model_version_by_alias(session, model_name, alias, database_name, schema_name)
    if current_version:
        session.sql(f"ALTER MODEL {model_name} VERSION {current_version} UNSET ALIAS").collect()
    # remove alias from needed version if exists
    current_alias = model_alias_by_version(session, model_name, version_name, database_name, schema_name)
    if current_alias:
        session.sql(f"ALTER MODEL {model_name} VERSION {version_name} UNSET ALIAS").collect()
    # set new alias
    session.sql(f"ALTER MODEL {model_name} VERSION {version_name} SET ALIAS = {alias}").collect()


def delete_model_version(
    session: Session,
    model_name: str,
    version_name: str,
    database_name: str,
    schema_name: str,
) -> None:
    session.sql(
        f"ALTER MODEL IDENTIFIER('{database_name}.{schema_name}.{model_name}') DROP VERSION {version_name}",
    ).collect()


def drop_model(
    session: Session,
    model_name: str,
    database_name: str,
    schema_name: str,
) -> None:
    session.sql(
        f"DROP MODEL IDENTIFIER('{database_name}.{schema_name}.{model_name}')",
    ).collect()
