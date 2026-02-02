from typing import Optional
from urllib.parse import urlparse

import mlflow
import requests


def is_mlflow_server_running(tracking_uri: Optional[str] = None) -> bool:
    """
    Check if MLflow tracking server is running and accessible.

    Args:
        tracking_uri: Optional MLflow tracking URI. If None, uses mlflow.get_tracking_uri()

    Returns:
        bool: True if server is running and accessible, False otherwise
    """
    if tracking_uri is None:
        tracking_uri = mlflow.get_tracking_uri()

    # If using local filesystem tracking, return True
    if tracking_uri.startswith("file://") or tracking_uri == "file":
        return True

    # Parse the tracking URI
    parsed_uri = urlparse(tracking_uri)
    if parsed_uri.scheme in ["http", "https"]:
        try:
            # Try to connect to the MLflow ping endpoint
            response = requests.get(f"{tracking_uri}/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    return False
