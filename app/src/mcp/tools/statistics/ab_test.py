"""A/B test statistical analysis tools."""

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
async def ab_test(
    dataset_id: str,
    group_column: str,
    metric_column: str,
    control_group: str,
    treatment_group: str,
    alpha: float = 0.05,
    metric_type: str = "continuous",
) -> str:
    """Perform A/B test statistical analysis.

    Analyzes the results of an A/B test to determine if there's a statistically
    significant difference between control and treatment groups.

    Supports two metric types:
    - continuous: Numerical metrics (e.g., revenue, time spent, clicks)
    - binary: Binary outcomes (e.g., conversion, signup, purchase)

    Args:
        dataset_id: Entity ID of the dataset containing A/B test results
        group_column: Column identifying groups (control vs treatment)
        metric_column: Column with the metric to analyze
        control_group: Value in group_column representing control group
        treatment_group: Value in group_column representing treatment group
        alpha: Significance level (default: 0.05)
        metric_type: Type of metric - "continuous" or "binary" (default: "continuous")

    Returns:
        ToolResponse with A/B test analysis results

    Example:
        "Analyze A/B test results for new checkout flow"
        → ab_test(
            dataset_id="test_results_123",
            group_column="variant",
            metric_column="converted",
            control_group="A",
            treatment_group="B",
            metric_type="binary"
        )

        "Test if new pricing increased revenue"
        → ab_test(
            dataset_id="revenue_test_123",
            group_column="pricing_variant",
            metric_column="revenue",
            control_group="old_pricing",
            treatment_group="new_pricing",
            metric_type="continuous"
        )
    """
    try:
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

        # Validate columns
        if group_column not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Column '{group_column}' not found",
                metadata={"error": "ColumnNotFound", "column": group_column},
                storage_hint="never",
            )

        if metric_column not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Column '{metric_column}' not found",
                metadata={"error": "ColumnNotFound", "column": metric_column},
                storage_hint="never",
            )

        # Extract control and treatment data
        control_data = df[df[group_column] == control_group][metric_column].dropna()
        treatment_data = df[df[group_column] == treatment_group][metric_column].dropna()

        if len(control_data) == 0:
            return ToolResponse(
                payload=None,
                summary=f"Error: No data found for control group '{control_group}'",
                metadata={"error": "EmptyGroup", "group": control_group},
                storage_hint="never",
            )

        if len(treatment_data) == 0:
            return ToolResponse(
                payload=None,
                summary=f"Error: No data found for treatment group '{treatment_group}'",
                metadata={"error": "EmptyGroup", "group": treatment_group},
                storage_hint="never",
            )

        logger.info(
            f"Performing A/B test: {control_group} (n={len(control_data)}) vs "
            f"{treatment_group} (n={len(treatment_data)})"
        )

        result = {}

        if metric_type == "continuous":
            # Continuous metric - use t-test
            control_mean = float(control_data.mean())
            treatment_mean = float(treatment_data.mean())
            control_std = float(control_data.std())
            treatment_std = float(treatment_data.std())

            # Perform t-test
            statistic, p_value = stats.ttest_ind(control_data, treatment_data)

            # Calculate effect size (Cohen's d)
            pooled_std = np.sqrt(
                ((len(control_data) - 1) * control_std**2 + (len(treatment_data) - 1) * treatment_std**2)
                / (len(control_data) + len(treatment_data) - 2)
            )
            cohens_d = (treatment_mean - control_mean) / pooled_std if pooled_std > 0 else 0.0

            # Calculate confidence interval for difference
            se_diff = pooled_std * np.sqrt(1 / len(control_data) + 1 / len(treatment_data))
            ci_margin = stats.t.ppf(1 - alpha / 2, len(control_data) + len(treatment_data) - 2) * se_diff
            diff = treatment_mean - control_mean
            ci_lower = diff - ci_margin
            ci_upper = diff + ci_margin

            # Calculate relative lift
            relative_lift = ((treatment_mean - control_mean) / control_mean * 100) if control_mean != 0 else 0.0

            result = {
                "test_type": "Independent Samples t-test",
                "metric_type": "continuous",
                "control": {
                    "group": control_group,
                    "n": len(control_data),
                    "mean": control_mean,
                    "std": control_std,
                    "min": float(control_data.min()),
                    "max": float(control_data.max()),
                },
                "treatment": {
                    "group": treatment_group,
                    "n": len(treatment_data),
                    "mean": treatment_mean,
                    "std": treatment_std,
                    "min": float(treatment_data.min()),
                    "max": float(treatment_data.max()),
                },
                "statistic": float(statistic),
                "p_value": float(p_value),
                "absolute_difference": diff,
                "relative_lift_percent": relative_lift,
                "confidence_interval": {
                    "level": 1 - alpha,
                    "lower": ci_lower,
                    "upper": ci_upper,
                },
                "effect_size": {
                    "cohens_d": float(cohens_d),
                    "interpretation": _interpret_cohens_d(cohens_d),
                },
            }

        elif metric_type == "binary":
            # Binary metric - use proportions test
            control_successes = int(control_data.sum())
            treatment_successes = int(treatment_data.sum())
            control_n = len(control_data)
            treatment_n = len(treatment_data)

            control_rate = control_successes / control_n if control_n > 0 else 0.0
            treatment_rate = treatment_successes / treatment_n if treatment_n > 0 else 0.0

            # Perform two-proportion z-test
            pooled_rate = (control_successes + treatment_successes) / (control_n + treatment_n)
            se_pooled = np.sqrt(pooled_rate * (1 - pooled_rate) * (1 / control_n + 1 / treatment_n))

            if se_pooled > 0:
                z_statistic = (treatment_rate - control_rate) / se_pooled
                p_value = 2 * (1 - stats.norm.cdf(abs(z_statistic)))
            else:
                z_statistic = 0.0
                p_value = 1.0

            # Calculate confidence interval for difference in proportions
            se_diff = np.sqrt(
                control_rate * (1 - control_rate) / control_n + treatment_rate * (1 - treatment_rate) / treatment_n
            )
            ci_margin = stats.norm.ppf(1 - alpha / 2) * se_diff
            diff = treatment_rate - control_rate
            ci_lower = diff - ci_margin
            ci_upper = diff + ci_margin

            # Calculate relative lift
            relative_lift = ((treatment_rate - control_rate) / control_rate * 100) if control_rate > 0 else 0.0

            # Calculate minimum detectable effect (MDE) with 80% power
            mde = _calculate_mde(control_rate, control_n, treatment_n, alpha=alpha, power=0.8)

            result = {
                "test_type": "Two-Proportion Z-Test",
                "metric_type": "binary",
                "control": {
                    "group": control_group,
                    "n": control_n,
                    "successes": control_successes,
                    "conversion_rate": control_rate,
                },
                "treatment": {
                    "group": treatment_group,
                    "n": treatment_n,
                    "successes": treatment_successes,
                    "conversion_rate": treatment_rate,
                },
                "statistic": float(z_statistic),
                "p_value": float(p_value),
                "absolute_difference": diff,
                "relative_lift_percent": relative_lift,
                "confidence_interval": {
                    "level": 1 - alpha,
                    "lower": ci_lower,
                    "upper": ci_upper,
                },
                "minimum_detectable_effect": {
                    "rate": mde,
                    "percent": mde * 100,
                    "description": f"Minimum effect size detectable with 80% power at α={alpha}",
                },
            }

        else:
            return ToolResponse(
                payload=None,
                summary=f"Error: Invalid metric_type '{metric_type}'. Must be 'continuous' or 'binary'",
                metadata={"error": "InvalidMetricType", "metric_type": metric_type},
                storage_hint="never",
            )

        # Add common fields
        result["alpha"] = alpha
        result["significant"] = result["p_value"] < alpha

        # Generate summary
        summary = "📊 A/B Test Analysis\n\n"
        summary += f"Test Type: {result['test_type']}\n"
        summary += f"Metric Type: {metric_type}\n"
        summary += f"Significance Level (α): {alpha}\n\n"

        summary += "Groups:\n"
        if metric_type == "continuous":
            summary += f"  • Control ({control_group}): n={result['control']['n']}, "
            summary += f"mean={result['control']['mean']:.4f}, std={result['control']['std']:.4f}\n"
            summary += f"  • Treatment ({treatment_group}): n={result['treatment']['n']}, "
            summary += f"mean={result['treatment']['mean']:.4f}, std={result['treatment']['std']:.4f}\n\n"
        else:
            summary += f"  • Control ({control_group}): n={result['control']['n']}, "
            summary += f"conversions={result['control']['successes']}, "
            summary += f"rate={result['control']['conversion_rate']:.2%}\n"
            summary += f"  • Treatment ({treatment_group}): n={result['treatment']['n']}, "
            summary += f"conversions={result['treatment']['successes']}, "
            summary += f"rate={result['treatment']['conversion_rate']:.2%}\n\n"

        summary += "Results:\n"
        summary += f"  • Test Statistic: {result['statistic']:.4f}\n"
        summary += f"  • P-value: {result['p_value']:.4f}\n"
        summary += f"  • Significant: {'Yes ✓' if result['significant'] else 'No ✗'}\n\n"

        summary += "Effect:\n"
        summary += f"  • Absolute Difference: {result['absolute_difference']:.4f}\n"
        summary += f"  • Relative Lift: {result['relative_lift_percent']:+.2f}%\n"
        summary += f"  • {int((1 - alpha) * 100)}% Confidence Interval: "
        summary += f"[{result['confidence_interval']['lower']:.4f}, {result['confidence_interval']['upper']:.4f}]\n"

        if metric_type == "continuous":
            summary += f"  • Effect Size (Cohen's d): {result['effect_size']['cohens_d']:.4f} "
            summary += f"({result['effect_size']['interpretation']})\n"
        else:
            summary += f"  • Minimum Detectable Effect: {result['minimum_detectable_effect']['percent']:.2f}%\n"

        # Interpretation
        summary += "\nInterpretation:\n"
        if result["significant"]:
            summary += f"  ⚠️  Statistically significant difference detected (p < {alpha})\n"
            if result["relative_lift_percent"] > 0:
                summary += (
                    f"  Treatment group performs {abs(result['relative_lift_percent']):.2f}% BETTER than control\n"
                )
            else:
                summary += (
                    f"  Treatment group performs {abs(result['relative_lift_percent']):.2f}% WORSE than control\n"
                )

            if metric_type == "binary":
                if result["confidence_interval"]["lower"] > 0:
                    summary += "  ✓ Confidence interval entirely positive - clear winner\n"
                elif result["confidence_interval"]["upper"] < 0:
                    summary += "  ⚠️ Confidence interval entirely negative - clear loser\n"
                else:
                    summary += "  ⚠️ Confidence interval crosses zero - effect uncertain\n"
        else:
            summary += f"  ✓  No statistically significant difference (p >= {alpha})\n"
            summary += "  Cannot conclude that treatment differs from control\n"

            if metric_type == "binary":
                if abs(result["relative_lift_percent"]) < abs(result["minimum_detectable_effect"]["percent"]):
                    summary += f"  Note: Observed effect ({abs(result['relative_lift_percent']):.2f}%) "
                    summary += (
                        f"is below minimum detectable effect ({result['minimum_detectable_effect']['percent']:.2f}%)\n"
                    )
                    summary += "  Consider increasing sample size for more power\n"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "control_group": control_group,
                "treatment_group": treatment_group,
                "significant": result["significant"],
                "relative_lift_percent": result["relative_lift_percent"],
            },
            storage_hint="session",
            suggested_name="ab_test_results",
        )

    except Exception as e:
        logger.exception(f"Error performing A/B test: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error performing A/B test: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )


def _interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d effect size."""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    if abs_d < 0.5:
        return "small"
    if abs_d < 0.8:
        return "medium"
    return "large"


def _calculate_mde(
    baseline_rate: float, n_control: int, n_treatment: int, alpha: float = 0.05, power: float = 0.8
) -> float:
    """Calculate minimum detectable effect for binary metrics.

    Args:
        baseline_rate: Control group conversion rate
        n_control: Control group sample size
        n_treatment: Treatment group sample size
        alpha: Significance level
        power: Statistical power (1 - beta)

    Returns:
        Minimum detectable effect (as a rate difference)
    """
    # Z-scores for alpha and power
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    # Pooled variance
    pooled_var = baseline_rate * (1 - baseline_rate) * (1 / n_control + 1 / n_treatment)

    # MDE calculation
    mde = (z_alpha + z_beta) * np.sqrt(pooled_var)

    return float(mde)
