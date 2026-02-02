import pandas as pd
import plotly.graph_objects as go


def plot_symmetric_granular_scatter(
    data: pd.DataFrame,
    dr_cr_col: str,
    account_col: str,
    target_col: str,
    date_col: str,
) -> go.Figure:
    if "abs" in target_col:
        data[target_col] = data[target_col].abs()

    fig = go.Figure()
    # data = data[data["COUNTERPARTY"] == '"0006000110042628"']
    dates = data[date_col].unique()

    data_in = data[data[dr_cr_col] == '"IN"']
    data_out = data[data[dr_cr_col] == '"OUT"'].assign(**{target_col: lambda x: -x[target_col]})

    colors = [
        "blue",  # date 1
        "red",  # date 2
        "green",  # date 3
        "orange",  # date 4
        "purple",  # date 5
        "cyan",  # date 6
        "magenta",  # date 7
        "yellow",  # date 8
        "black",  # date 9
        "gray",  # date 10
        "brown",  # date 11
        "pink",  # date 12
    ]

    for i, date in enumerate(dates):
        data_in_date = data_in[data_in[date_col] == date]
        data_out_date = data_out[data_out[date_col] == date]

        fig.add_trace(
            go.Scatter(
                x=data_in_date[target_col],
                y=data_in_date[account_col],
                mode="markers",
                name=date,
                marker=dict(color=colors[i % len(colors)]),
                # texttemplate=f"{date_col}: {date}",
                # textposition="top center",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data_out_date[target_col],
                y=data_out_date[account_col],
                mode="markers",
                # name=date,
                marker=dict(color=colors[i % len(colors)]),
                # texttemplate=f"{date_col}: {date}",
                # textposition="top center",
            )
        )

    max_val = data[target_col].max()
    tick_vals = [-max_val, -max_val / 2, 0, max_val / 2, max_val]
    tick_text = [str(abs(v)) for v in tick_vals]
    fig.update_layout(
        title="Debit vs Credit",
        xaxis=dict(
            title="Amount", tickvals=tick_vals, ticktext=tick_text, zeroline=True, zerolinewidth=2, zerolinecolor="gray"
        ),
        yaxis=dict(title="Counterparty"),
        height=4000,
    )
    return fig
