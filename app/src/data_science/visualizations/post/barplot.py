import pandas as pd
import plotly.graph_objects as go


def plot_barplot(
    df: pd.DataFrame,
    is_credit: bool | None = None,
    account_col: str = "COUNTERPARTY",
    erorr_col: str = "ABS_ERROR",
    actuals_col: str = "ACTUALS",
    date_col: str = "DATE",
    direction_col: str = "DIRECTION",
    is_best: bool = True,
    top_n: int = 10,
):
    if is_credit is not None:
        df = df[df[direction_col] == ('"IN"' if is_credit else '"OUT"')]
    df_error = (
        df.groupby([account_col])
        .agg({erorr_col: ("mean", "std")})
        .sort_values([(erorr_col, "mean")], ascending=is_best)
        .head(top_n)
        .reset_index()
    )
    # change level of columns from multiindex to single index
    df_error.columns = [account_col, f"{erorr_col}_mean", f"{erorr_col}_std"]

    df_count = df.groupby([account_col, date_col]).agg({actuals_col: "sum"}).reset_index() if is_credit is None else df
    df_count = df_count.groupby([account_col]).agg({actuals_col: lambda x: (x != 0).sum()}).reset_index()

    df_error = df_error.merge(df_count, on=account_col, how="left")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_error[account_col],
            y=df_error[f"{erorr_col}_mean"],
            error_y=dict(type="data", array=df_error[f"{erorr_col}_std"]),
            name="Mean Error",
        )
    )

    fig.add_trace(
        go.Bar(
            x=df_error[account_col],
            y=df_error[actuals_col],
            name="Count of Non-Zero Actuals",
            marker_color="rgba(255, 0, 0, 0.5)",
            yaxis="y2",
        )
    )
    fig.update_layout(
        title=f"Top {top_n} {'Credit' if is_credit else 'Debit'} Accounts by Mean Error",
        xaxis_title=account_col,
        yaxis_title=erorr_col,
        barmode="group",
    )
    fig.update_xaxes(tickangle=-45)
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height=600,
        width=800,
        template="plotly_white",
        yaxis2=dict(
            title=actuals_col,
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=True,
            ticks="",
            range=[0, df_error[actuals_col].max()],
            scaleanchor="y",
            scaleratio=df_error[f"{erorr_col}_mean"].max() / df_error[actuals_col].max(),
        ),
    )
    return fig
