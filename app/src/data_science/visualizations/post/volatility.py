import numpy as np
import pandas as pd
import plotly.graph_objects as go


def plot_volatility(
    df: pd.DataFrame,
    account_col: str = "COUNTERPARTY",
    direction_col: str = "DIRECTION",
    actuals_col: str = "ACTUALS",
) -> go.Figure:
    """
    Volatility vs Accuracy
    Scatter plot of volatility vs accuracy:
    - each point is a account, transaction direction
    - x-axis: volatility (coefficient of variation of actuals)
    - y-axis: accuracy (mean absolute error of actuals)
    - bubble size: number of transactions
    - color: direction of the transaction (IN or OUT)
    """

    df = df.copy()
    df = (
        df.groupby([account_col, direction_col])
        .agg(
            {
                actuals_col: ["mean", "std", "count", "sum"],
                "ABS_ERROR": "mean",
            }
        )
        .reset_index()
    )

    df.columns = [
        account_col,
        direction_col,
        "mean_actuals",
        "std_actuals",
        "count_transactions",
        "total_actuals",
        "mean_abs_error",
    ]

    df["volatility"] = df.apply(
        lambda row: row["std_actuals"] / row["mean_actuals"] if row["mean_actuals"] != 0 else 0, axis=1
    )

    fig = go.Figure()
    for direction in df[direction_col].unique():
        df_direction = df[df[direction_col] == direction]

        fig.add_trace(
            go.Scatter(
                y=df_direction["volatility"],
                x=df_direction["mean_abs_error"],
                mode="markers",
                name=f"Direction: {direction}",
                marker=dict(
                    size=df_direction["total_actuals"]
                    * 100
                    / df_direction["total_actuals"].max(),  # Adjust size for better visibility
                    #     color=np.where(direction == '"IN"', "blue", "red"),
                    opacity=0.6,
                ),
                # text=df_direction[account_col],
            )
        )
    fig.update_layout(
        title="Volatility vs Accuracy",
        yaxis_title="Volatility (Coefficient of Variation)",
        xaxis_title="Mean Absolute Error",
        height=800,
        width=1200,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(title=direction_col),
    )
    return fig
