import numpy as np
import pandas as pd
import plotly.graph_objects as go


def plot_skewed_scatter(
    df: pd.DataFrame,
    date_col: str = "DATE",
    account_col: str = "COUNTERPARTY",
    direction_col: str = "DIRECTION",
    actuals_col: str = "ACTUALS",
    forecast_col: str = "FORECASTS",
    error_col: str = "ABS_ERROR",
):
    df = df.copy()
    df["label"] = df.apply(lambda row: f"{row[account_col]} ({row[date_col]}) - (error: {row[error_col]})", axis=1)

    directions = df[direction_col].unique()
    fig = go.Figure()
    for direction in directions:
        if direction not in ['"IN"', '"OUT"']:
            raise ValueError(f"Invalid direction value: {direction}. Expected 'IN' or 'OUT'.")
        df_filtered = df[df[direction_col] == direction]

        # Create scatter plot for IN direction
        fig.add_trace(
            go.Scatter(
                x=df_filtered[actuals_col],
                y=df_filtered[forecast_col],
                mode="markers",
                name=f"scater: {direction}",
                text=df_filtered["label"],
                textposition="top center",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=df[actuals_col],
            y=df[actuals_col],
            name="y=x",
        )
    )

    fig.update_layout(
        title="Skewed Scatter Plot of Actuals vs Forecast",
        xaxis_title=actuals_col,
        yaxis_title=forecast_col,
        height=800,
        width=1200,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    return fig
