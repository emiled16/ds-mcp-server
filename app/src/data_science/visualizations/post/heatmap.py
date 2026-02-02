import numpy as np
import pandas as pd
import plotly.graph_objects as go


def plot_heatmap(
    df: pd.DataFrame,
    date_col: str = "DATE",
    account_col: str = "COUNTERPARTY",
    error_col: str = "ABS_ERROR",
    is_credit: bool | None = None,
):
    if is_credit is None:
        # TODO: logic needs to be implemented
        return

    df = df.copy()
    df = df[df["DIRECTION"] == '"IN"'] if is_credit else df[df["DIRECTION"] == '"OUT"']

    fig = go.Figure()

    fig.add_trace(
        go.Heatmap(
            x=df[date_col],
            y=df[account_col],
            z=df[error_col],
            colorscale="Viridis",
            colorbar=dict(title=error_col),
            hoverongaps=False,
        )
    )

    fig.update_layout(
        title=f"{'Credit' if is_credit else 'Debit'} Accounts Heatmap",
        xaxis_title=date_col,
        yaxis_title=account_col,
        height=800,
        width=1200,
    )
    fig.update_xaxes(tickangle=-45)

    return fig
