"""Confidence interval calculation tools."""

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def confidence_interval(
    dataset_id: str,
    column: str,
    confidence_level: float = 0.95,
    interval_type: str = "mean",
    group_column: str | None = None,
) -> str:
    """Calculate confidence intervals for statistical estimates.

    Computes confidence intervals for various statistics using bootstrapping
    or parametric methods.

    Supported interval types:
    - mean: Confidence interval for the mean
    - proportion: Confidence interval for a proportion (binary data)
    - median: Confidence interval for the median (bootstrap)
    - std: Confidence interval for the standard deviation
    - difference: Confidence interval for difference between groups (requires group_column)

    Args:
        dataset_id: Entity ID of the dataset
        column: Column to analyze
        confidence_level: Confidence level (e.g., 0.95 for 95% CI)
        interval_type: Type of interval - "mean", "proportion", "median", "std", "difference"
        group_column: Column with group labels (required for "difference" type)

    Returns:
        ToolResponse with confidence interval results

    Example:
        "Calculate 95% confidence interval for average revenue"
        → confidence_interval(
            dataset_id="sales_123",
            column="revenue",
            interval_type="mean"
        )

        "Calculate 99% confidence interval for conversion rate"
        → confidence_interval(
            dataset_id="users_123",
            column="converted",
            confidence_level=0.99,
            interval_type="proportion"
        )

        "Calculate confidence interval for difference in engagement by region"
        → confidence_interval(
            dataset_id="engagement_123",
            column="time_spent",
            interval_type="difference",
            group_column="region"
        )
    """
    try:
        # Validate confidence level
        if not 0 < confidence_level < 1:
            return ToolResponse(
                payload=None,
                summary=f"Error: Confidence level must be between 0 and 1, got {confidence_level}",
                metadata={"error": "InvalidConfidenceLevel"},
                storage_hint="never",
            )

        # Get dataset
        registry = get_repository_registry()
        entity = await registry.get("tool_response", dataset_id)

        if not entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Dataset '{dataset_id}' not found",
                metadata={"error": "NotFound", "dataset_id": dataset_id},
                storage_hint="never",
            )

        df = entity.payload
        if not isinstance(df, pd.DataFrame):
            return ToolResponse(
                payload=None,
                summary=f"Error: Entity '{dataset_id}' is not a DataFrame",
                metadata={"error": "TypeError", "entity_id": dataset_id},
                storage_hint="never",
            )

        # Validate column
        if column not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Column '{column}' not found",
                metadata={"error": "ColumnNotFound", "column": column},
                storage_hint="never",
            )

        logger.info(f"Calculating {interval_type} confidence interval for column '{column}'")

        result = {}
        alpha = 1 - confidence_level

        if interval_type == "mean":
            # Confidence interval for mean
            data = df[column].dropna()
            n = len(data)
            mean = float(data.mean())
            std = float(data.std(ddof=1))
            se = std / np.sqrt(n)

            # Use t-distribution for small samples
            t_critical = stats.t.ppf(1 - alpha / 2, n - 1)
            margin = t_critical * se
            ci_lower = mean - margin
            ci_upper = mean + margin

            result = {
                "interval_type": "mean",
                "statistic": mean,
                "standard_error": se,
                "confidence_level": confidence_level,
                "lower_bound": ci_lower,
                "upper_bound": ci_upper,
                "margin_of_error": margin,
                "sample_size": n,
                "method": "t-distribution",
            }

        elif interval_type == "proportion":
            # Confidence interval for proportion (Wilson score interval)
            data = df[column].dropna()
            n = len(data)
            successes = int(data.sum())
            p = successes / n if n > 0 else 0.0

            # Wilson score interval (more accurate than normal approximation)
            z = stats.norm.ppf(1 - alpha / 2)
            denominator = 1 + z**2 / n
            center = (p + z**2 / (2 * n)) / denominator
            margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator

            ci_lower = center - margin
            ci_upper = center + margin

            result = {
                "interval_type": "proportion",
                "statistic": p,
                "successes": successes,
                "confidence_level": confidence_level,
                "lower_bound": max(0, ci_lower),  # Clamp to [0, 1]
                "upper_bound": min(1, ci_upper),
                "margin_of_error": margin,
                "sample_size": n,
                "method": "Wilson score",
            }

        elif interval_type == "median":
            # Confidence interval for median using bootstrap
            data = df[column].dropna().values
            n = len(data)
            median = float(np.median(data))

            # Bootstrap with 10000 resamples
            n_bootstrap = 10000
            bootstrap_medians = []
            rng = np.random.default_rng(42)  # Fixed seed for reproducibility

            for _ in range(n_bootstrap):
                resample = rng.choice(data, size=n, replace=True)
                bootstrap_medians.append(np.median(resample))

            bootstrap_medians = np.array(bootstrap_medians)

            # Percentile method
            ci_lower = float(np.percentile(bootstrap_medians, 100 * alpha / 2))
            ci_upper = float(np.percentile(bootstrap_medians, 100 * (1 - alpha / 2)))

            result = {
                "interval_type": "median",
                "statistic": median,
                "confidence_level": confidence_level,
                "lower_bound": ci_lower,
                "upper_bound": ci_upper,
                "sample_size": n,
                "method": "bootstrap (10000 resamples)",
            }

        elif interval_type == "std":
            # Confidence interval for standard deviation using chi-square
            data = df[column].dropna()
            n = len(data)
            std = float(data.std(ddof=1))
            variance = std**2

            # Chi-square distribution
            chi2_lower = stats.chi2.ppf(alpha / 2, n - 1)
            chi2_upper = stats.chi2.ppf(1 - alpha / 2, n - 1)

            # CI for variance
            var_lower = (n - 1) * variance / chi2_upper
            var_upper = (n - 1) * variance / chi2_lower

            # CI for standard deviation
            ci_lower = np.sqrt(var_lower)
            ci_upper = np.sqrt(var_upper)

            result = {
                "interval_type": "standard_deviation",
                "statistic": std,
                "confidence_level": confidence_level,
                "lower_bound": ci_lower,
                "upper_bound": ci_upper,
                "sample_size": n,
                "method": "chi-square distribution",
            }

        elif interval_type == "difference":
            # Confidence interval for difference between groups
            if group_column is None:
                return ToolResponse(
                    payload=None,
                    summary="Error: 'difference' interval type requires group_column",
                    metadata={"error": "MissingGroupColumn"},
                    storage_hint="never",
                )

            if group_column not in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Column '{group_column}' not found",
                    metadata={"error": "ColumnNotFound", "column": group_column},
                    storage_hint="never",
                )

            # Get unique groups
            groups = df[group_column].unique()
            if len(groups) != 2:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: 'difference' requires exactly 2 groups, found {len(groups)}",
                    metadata={"error": "InvalidGroupCount", "n_groups": len(groups)},
                    storage_hint="never",
                )

            group1_name, group2_name = groups[0], groups[1]
            group1_data = df[df[group_column] == group1_name][column].dropna()
            group2_data = df[df[group_column] == group2_name][column].dropna()

            n1 = len(group1_data)
            n2 = len(group2_data)
            mean1 = float(group1_data.mean())
            mean2 = float(group2_data.mean())
            std1 = float(group1_data.std(ddof=1))
            std2 = float(group2_data.std(ddof=1))

            # Pooled standard error
            pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
            se_diff = pooled_std * np.sqrt(1 / n1 + 1 / n2)

            # t-distribution
            df_value = n1 + n2 - 2
            t_critical = stats.t.ppf(1 - alpha / 2, df_value)

            difference = mean2 - mean1
            margin = t_critical * se_diff
            ci_lower = difference - margin
            ci_upper = difference + margin

            result = {
                "interval_type": "difference_of_means",
                "statistic": difference,
                "standard_error": se_diff,
                "confidence_level": confidence_level,
                "lower_bound": ci_lower,
                "upper_bound": ci_upper,
                "margin_of_error": margin,
                "groups": {
                    str(group1_name): {"n": n1, "mean": mean1, "std": std1},
                    str(group2_name): {"n": n2, "mean": mean2, "std": std2},
                },
                "method": "t-distribution (pooled variance)",
            }

        else:
            return ToolResponse(
                payload=None,
                summary=f"Error: Unknown interval type '{interval_type}'",
                metadata={"error": "InvalidIntervalType", "interval_type": interval_type},
                storage_hint="never",
            )

        # Generate summary
        summary = "📊 Confidence Interval\n\n"
        summary += f"Type: {result['interval_type'].replace('_', ' ').title()}\n"
        summary += f"Confidence Level: {confidence_level:.0%}\n"
        summary += f"Method: {result['method']}\n\n"

        summary += "Results:\n"
        summary += f"  • Estimate: {result['statistic']:.4f}\n"
        summary += f"  • {confidence_level:.0%} CI: [{result['lower_bound']:.4f}, {result['upper_bound']:.4f}]\n"

        if "margin_of_error" in result:
            summary += f"  • Margin of Error: ±{result['margin_of_error']:.4f}\n"

        if "standard_error" in result:
            summary += f"  • Standard Error: {result['standard_error']:.4f}\n"

        summary += f"  • Sample Size: {result.get('sample_size', 'N/A')}\n"

        if interval_type == "proportion":
            summary += f"  • Successes: {result['successes']}\n"

        if interval_type == "difference":
            summary += "\nGroups:\n"
            for group_name, group_stats in result["groups"].items():
                summary += f"  • {group_name}: n={group_stats['n']}, mean={group_stats['mean']:.4f}, std={group_stats['std']:.4f}\n"

        # Interpretation
        summary += "\nInterpretation:\n"
        summary += (
            f"  We are {confidence_level:.0%} confident that the true {result['interval_type'].replace('_', ' ')} "
        )
        summary += f"lies between {result['lower_bound']:.4f} and {result['upper_bound']:.4f}.\n"

        if interval_type == "difference":
            if result["lower_bound"] > 0 and result["upper_bound"] > 0:
                summary += f"  ✓ The interval is entirely positive, indicating {list(result['groups'].keys())[1]} "
                summary += f"is likely higher than {list(result['groups'].keys())[0]}\n"
            elif result["lower_bound"] < 0 and result["upper_bound"] < 0:
                summary += f"  ✓ The interval is entirely negative, indicating {list(result['groups'].keys())[1]} "
                summary += f"is likely lower than {list(result['groups'].keys())[0]}\n"
            else:
                summary += "  ⚠️ The interval includes zero, so the difference may not be statistically significant\n"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "column": column,
                "interval_type": interval_type,
                "confidence_level": confidence_level,
            },
            storage_hint="session",
            suggested_name=f"ci_{interval_type}",
        )

    except Exception as e:
        logger.exception(f"Error calculating confidence interval: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error calculating confidence interval: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )
