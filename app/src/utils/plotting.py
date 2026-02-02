"""Plotting utilities for saving and managing visualizations."""

import base64
import io
import os
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
from loguru import logger

# Use non-interactive backend
matplotlib.use("Agg")

# MinIO configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "mlflow")


def save_plot_to_minio(fig: plt.Figure, plot_name: str) -> tuple[str, str]:
    """Save a matplotlib figure to MinIO and return the URL and object key.

    Args:
        fig: Matplotlib figure to save
        plot_name: Base name for the plot file

    Returns:
        Tuple of (object_key, url)
    """
    try:
        from minio import Minio

        # Create MinIO client
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )

        # Ensure bucket exists
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"plots/{plot_name}_{timestamp}.png"

        # Save figure to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)

        # Upload to MinIO
        client.put_object(
            MINIO_BUCKET,
            object_name,
            buf,
            length=buf.getbuffer().nbytes,
            content_type="image/png",
        )

        # Generate URL
        url = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"

        logger.info(f"Saved plot to MinIO: {url}")
        return object_name, url

    except Exception as e:
        logger.exception(f"Error saving plot to MinIO: {e}")
        # Fallback: return base64 encoded image
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode()
        return "base64", f"data:image/png;base64,{img_base64}"


def close_figure(fig: plt.Figure) -> None:
    """Close a matplotlib figure to free memory."""
    plt.close(fig)
