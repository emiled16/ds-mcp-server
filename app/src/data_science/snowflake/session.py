import os
from pathlib import Path
from typing import Any, Dict

from snowflake.snowpark import Session

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
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "client_session_keep_alive": True,
    }

    print("Creds")
    print(creds)

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

        # Key-pair
        if private_key_file := os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"):
            creds["private_key_file"] = private_key_file
            if passphrase := os.getenv("PRIVATE_KEY_PASSPHRASE"):
                creds["private_key_file_pwd"] = passphrase
    else:
        # Basic Auth
        creds["user"] = os.getenv("SNOWFLAKE_USER")
        creds["password"] = os.getenv("SNOWFLAKE_PASSWORD")

        creds["authenticator"] = "username_password_mfa"  # todo: manage better

    creds = {
        "account": "cms_prod.ca-central-1.aws",
        "user": "emile",
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": "COMPUTE_WH",
        "database": "MAXA_SNBX",
        "schema": "SNBX_EMILE_DIMAS",
        "role": "SYSADMIN",
        "client_session_keep_alive": True,
        # "network_timeout": 600,
        "authenticator": "username_password_mfa",  # or "snowflake"
    }
    return creds


def create_snowpark_session(credentials_file: Path = Path(SNOWFLAKE_SESSION_CREDENTIALS_FILE_NAME)) -> Session:
    # creds = _make_snowpark_creds(credentials_file)
    creds = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "client_session_keep_alive": True,
        # "network_timeout": 600,
        "authenticator": "username_password_mfa",  # or "snowflake"
    }
    return Session.builder.configs(creds).create()


def is_inside_snowflake() -> bool:
    in_snowpark_container = Path(SNOWFLAKE_SESSION_CREDENTIALS_FILE_NAME).exists()
    in_streamlit_in_snowflake = os.getenv("HOME") == "/home/udf"
    return in_snowpark_container or in_streamlit_in_snowflake
