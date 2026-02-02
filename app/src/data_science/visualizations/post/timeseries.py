import pandas as pd
import plotly.graph_objects as go


def plot_timeseries(
    data: pd.DataFrame,
    x_axis_col: str,
    y_axis_cols: str,
    selection: dict[str, list[str]],
    **kwargs: dict,
) -> go.Figure:
    fig = go.Figure()

    filtered_data = data.copy()
    for k, v in selection.items():
        if len(v) > 0:
            filtered_data = filtered_data[filtered_data[k].isin(v)]

    filtered_data = (
        filtered_data.groupby([x_axis_col])
        .agg({col: "sum" for col in y_axis_cols})
        .reset_index()
        .sort_values([x_axis_col])
    )

    for col in y_axis_cols:
        fig.add_trace(go.Scatter(x=filtered_data[x_axis_col], y=filtered_data[col], mode="lines+markers", name=col))

    fig.update_layout(**kwargs)

    return fig
