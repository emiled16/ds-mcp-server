import json
import uuid
from typing import Annotated, Any, Literal

import requests
from pydantic import BaseModel, Field
from src.data_science.snowflake.cortex.cortex_semantic_model import CortexSemanticModel
from src.data_science.snowflake.session import is_inside_snowflake
from src.data_science.snowflake_optional import get_active_session, require_snowflake

# Cortex Analyst REST API
# => https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api#request-body


class CortexAnalystMessageText(BaseModel):
    type: Literal["text"] = "text"
    text: str


ExecutableVerifiedQuery = str
"""SQL query with the logical table CTEs (can be executed)."""


class CortexAnalystMessageSql(BaseModel):
    type: Literal["sql"] = "sql"
    statement: ExecutableVerifiedQuery
    confidence: Any | None = None


class CortexAnalystMessageSuggestion(BaseModel):
    type: Literal["suggestions"] = "suggestions"
    suggestions: list[str]


CortexAnalystMessageContent = Annotated[
    CortexAnalystMessageText | CortexAnalystMessageSql | CortexAnalystMessageSuggestion,
    Field(discriminator="type"),
]


class CortexAnalystMessage(BaseModel):
    role: str  # user, analyst, system
    content: list[CortexAnalystMessageContent]

    @staticmethod
    def user_prompt(text: str) -> "CortexAnalystMessage":
        return CortexAnalystMessage(role="user", content=[CortexAnalystMessageText(text=text)])


def cortex_analyst(semantic_model: CortexSemanticModel, messages: list[CortexAnalystMessage]) -> CortexAnalystMessage:
    """Calls the Cortex Analyst API.

    Ref: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api
    """
    require_snowflake()
    request = CortexAnalystRequest(messages=messages, semantic_model=semantic_model.to_yaml())

    cortex_analyst_api = _cortex_analyst_native_app_api if is_inside_snowflake() else _cortex_analyst_rest_api

    request_id, status_code, response_json = cortex_analyst_api(request)

    if status_code >= 400:
        raise ValueError(
            f"Failed to request Cortex Analyst\n\n{request=}\n\n{request_id=}\n\n{status_code=}\n\n{response_json=}",
        )

    return CortexAnalystResponse.model_validate(response_json).message


class CortexAnalystRequest(BaseModel):
    messages: list[CortexAnalystMessage]
    semantic_model_file: str | None = None
    semantic_model: str | None = None


class CortexAnalystResponse(BaseModel):
    message: CortexAnalystMessage
    request_id: str


def _cortex_analyst_native_app_api(request: CortexAnalystRequest) -> tuple[str, int, dict]:
    """Cortex Analyst API from Streamlit in Snowflake."""
    try:
        import _snowflake  # type: ignore
    except ImportError as e:
        raise ImportError(
            "Cortex Analyst native app API requires running inside Snowflake (e.g. Streamlit in Snowflake)."
        ) from e

    request_body = request.model_dump(mode="json")
    resp = _snowflake.send_snow_api_request("POST", "/api/v2/cortex/analyst/message", {}, {}, request_body, {}, 30000)

    request_id = str(uuid.uuid4())
    status_code = resp["status"]
    response_json = json.loads(resp["content"])
    return request_id, status_code, response_json


def _cortex_analyst_rest_api(request: CortexAnalystRequest) -> tuple[str, int, dict]:
    """Ref: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api"""
    session = get_active_session()
    if not (rest_connection := session.connection.rest):
        raise ValueError("REST connection unavailable.")
    if not (session_token := rest_connection.token):
        raise ValueError("REST token unavailable.")

    response = requests.post(
        url=f"https://{session.connection.host}/api/v2/cortex/analyst/message",
        json=request.model_dump(mode="json"),
        headers={"Authorization": f'Snowflake Token="{session_token}"', "Content-Type": "application/json"},
        timeout=60.0,
    )
    request_id = str(response.headers.get("X-Snowflake-Request-Id"))
    status_code = response.status_code

    try:
        response_json = response.json()
    except requests.JSONDecodeError as error:
        raise ValueError(
            f"Cannot parse Cortex Analyst response:\n{request_id=}\n{status_code=}\n{response.text}",
        ) from error

    return request_id, status_code, response_json
