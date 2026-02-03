"""Plotting utilities for saving and managing visualizations."""

import base64
import io
import os
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
from loguru import logger

from src.storage.backends.dispatcher import get_object_store

# Use non-interactive backend
matplotlib.use("Agg")

# Object store bucket (used for both MinIO and GCS backends)
OBJECT_STORE_BUCKET = os.getenv("OBJECT_STORE_BUCKET") or os.getenv("MINIO_BUCKET", "mlflow")


async def save_plot_to_minio(fig: plt.Figure, plot_name: str) -> tuple[str, str]:
    """Save a matplotlib figure to the configured object store (MinIO or GCS) and return the object key and URL.

    Uses OBJECT_STORE_BACKEND (minio | gcs). Bucket from OBJECT_STORE_BUCKET or MINIO_BUCKET.

    Args:
        fig: Matplotlib figure to save
        plot_name: Base name for the plot file

    Returns:
        Tuple of (object_key, url)
    """
    try:
        store = get_object_store()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"plots/{plot_name}_{timestamp}.png"

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        data = buf.getvalue()

        await store.put(OBJECT_STORE_BUCKET, object_name, data)

        backend = os.getenv("OBJECT_STORE_BACKEND", "minio").lower()
        if backend == "minio":
            endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            url = f"http://{endpoint}/{OBJECT_STORE_BUCKET}/{object_name}"
        else:
            gcs_bucket = os.getenv("GCS_ARTIFACTS_BUCKET", "")
            url = f"gs://{gcs_bucket}/{OBJECT_STORE_BUCKET}/{object_name}"

        logger.info(f"Saved plot to object store: {url}")
        return object_name, url

    except Exception as e:
        logger.exception(f"Error saving plot to object store: {e}")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode()
        return "base64", f"data:image/png;base64,{img_base64}"


def close_figure(fig: plt.Figure) -> None:
    """Close a matplotlib figure to free memory."""
    plt.close(fig)
