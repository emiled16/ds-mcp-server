import numpy as np
import pandas as pd
import plotly.graph_objects as go


def plot_cumulative_counterparty(
    df: pd.DataFrame,
    date_col: str = "DATE",
    account_col: str = "COUNTERPARTY",
    direction_col: str = "DIRECTION",
    actuals_col: str = "ACTUALS",
    aggregation: callable = np.sum,
    selection: dict[str, list[str]] | None = None,
) -> None:
    df = df.copy()
    if selection is not None and len(selection) > 0:
        for k, v in selection.items():
            if len(v) > 0:
                df = df[df[k].isin(v)]
    cum_df = (
        df.groupby([account_col, date_col])
        .apply(
            lambda _d: _d[_d[direction_col] == '"IN"'][actuals_col].sum()
            - _d[_d[direction_col] == '"OUT"'][actuals_col].sum()
        )
        .abs()
        .reset_index()
        .rename(columns={0: "FLOW"})
        .groupby(account_col)
        .agg({"FLOW": aggregation})
        .sort_values("FLOW", ascending=False)
        .reset_index()
        .assign(
            CUM_FLOW=lambda _d: _d["FLOW"].cumsum(),
            TOTAL=lambda _d: _d["FLOW"].sum(),
            CUM_PCT=lambda _d: _d["CUM_FLOW"] / _d["TOTAL"],
            RANK=lambda _d: _d["FLOW"].rank(method="first", ascending=False),
            LABEL=lambda _d: "#"
            + _d["RANK"].astype(int).astype(str)
            + " - "
            + _d[account_col]
            + " ( flow: "
            + _d["FLOW"].astype(str)
            + ")",
        )
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=cum_df[account_col],
            y=cum_df["CUM_PCT"],
            mode="lines+markers",
            name="Cumulative Percentage",
            text=cum_df["LABEL"],
            textposition="top center",
        )
    )
    fig.update_layout(
        title="Cumulative Counterparty Flow",
        xaxis_title=account_col,
        yaxis_title="Cumulative Percentage",
        template="plotly_white",
        height=600,
        width=800,
        margin=dict(l=50, r=50, t=50, b=50),
    )
    return fig
