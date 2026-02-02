import os
from pathlib import Path
from typing import Any, Dict

# from src.data_science.snowflake.session import create_snowpark_session
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.exceptions import SnowparkSessionException

SNOWFLAKE_SESSION_CREDENTIALS_FILE_NAME = "/snowflake/session/token"


def _make_snowpark_creds(credentials_file: Path) -> Dict[str, Any]:
    """
    Ref: https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect
    """
    creds = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "client_session_keep_alive": True,
    }

    if credentials_file.is_file():
        # Token
        creds["host"] = os.getenv("SNOWFLAKE_HOST")
        creds["port"] = os.getenv("SNOWFLAKE_PORT")
        creds["protocol"] = "https"
        creds["authenticator"] = "oauth"
        creds["token"] = credentials_file.read_text()
    elif snowflake_authenticator := os.getenv("SNOWFLAKE_AUTHENTICATOR"):
        # SSO
        creds["user"] = os.getenv("SNOWFLAKE_USER")
        creds["authenticator"] = snowflake_authenticator
        creds["role"] = os.getenv("SNOWFLAKE_ROLE")

        # Key-pair
        if private_key_file := os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"):
            creds["private_key_file"] = private_key_file
            if passphrase := os.getenv("PRIVATE_KEY_PASSPHRASE"):
                creds["private_key_file_pwd"] = passphrase
    else:
        # Basic Auth
        creds["user"] = os.getenv("SNOWFLAKE_USER")
        creds["password"] = os.getenv("SNOWFLAKE_PASSWORD")
        creds["role"] = os.getenv("SNOWFLAKE_ROLE")
    return creds


def create_snowpark_session(credentials_file: Path = Path(SNOWFLAKE_SESSION_CREDENTIALS_FILE_NAME)) -> Session:
    creds = _make_snowpark_creds(credentials_file)
    return Session.builder.configs(creds).create()


def snowpark_session() -> Session:
    """Either return the available Snowpark session or create a new one."""
    try:
        return get_active_session()
    except SnowparkSessionException:
        return create_snowpark_session()


def snowflake_session(query_tag: str = "snowpark", env_file: str = ".env") -> Session:
    """Either return the available Snowpark session or create a new one."""
    try:
        session = get_active_session()
    except SnowparkSessionException:
        session = create_snowpark_session()
        session.query_tag = query_tag

    return session
