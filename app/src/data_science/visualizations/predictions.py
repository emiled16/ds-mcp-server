import itertools

import pandas as pd
import plotly.graph_objects as go


def plot_predictions(
    predictions: pd.DataFrame,
    actual_column: str,
    prediction_column: str,
    date_column: str,
    split_column: str,
) -> go.Figure:
    fig = go.Figure()
    split_values = predictions[split_column].unique()
    relevant_indexes_name = list(set(predictions.index.names) - {f"{date_column}_idx"})
    relevant_indexes_values = [
        predictions.index.get_level_values(relevant_index_name).unique()
        for relevant_index_name in relevant_indexes_name
    ]
    combinations = list(itertools.product(*relevant_indexes_values, split_values))

    line_styles = ["dash", "solid", "dot", "dashdot"]

    for i, combination in enumerate(combinations):
        filtered_data = predictions[predictions[split_column] == combination[-1]]
        for j, index in enumerate(relevant_indexes_name):
            filtered_data = filtered_data[filtered_data.index.get_level_values(index) == combination[j]]

        line_style = line_styles[i % len(line_styles)]
        fig.add_trace(
            go.Scatter(
                x=filtered_data.index.get_level_values(f"{date_column}_idx").to_list(),
                y=filtered_data[prediction_column],
                name=f"Prediction ({', '.join(combination)})",
                mode="lines",
                line=dict(color="red", dash=line_style),
            ),
        )

        # Add actual trace for this split
        fig.add_trace(
            go.Scatter(
                x=filtered_data.index.get_level_values(f"{date_column}_idx").to_list(),
                y=filtered_data[actual_column],
                name=f"Actual ({', '.join(combination)})",
                mode="lines",
                line=dict(color="blue", dash=line_style),
            ),
        )

    fig.update_layout(title=f"Predictions by {split_column}", xaxis_title="Date", yaxis_title="Value")
    return fig
