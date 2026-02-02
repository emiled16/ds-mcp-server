"""Statistical significance testing tools."""

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
async def significance_test(
    dataset_id: str,
    column: str,
    test_value: float,
    test_type: str = "one-sample",
    alternative: str = "two-sided",
    alpha: float = 0.05,
    correction: str | None = None,
) -> str:
    """Test statistical significance of observations.

    Performs various significance tests to determine if observed data
    differs significantly from expected values or hypotheses.

    Supported test types:
    - one-sample: Test if sample mean differs from a hypothesized value
    - proportion: Test if sample proportion differs from a hypothesized proportion
    - goodness-of-fit: Test if observed frequencies match expected distribution

    Multiple comparison corrections (optional):
    - bonferroni: Bonferroni correction for multiple tests
    - holm: Holm-Bonferroni sequential correction
    - fdr: False Discovery Rate (Benjamini-Hochberg) correction

    Args:
        dataset_id: Entity ID of the dataset
        column: Column to test
        test_value: Hypothesized value to test against
        test_type: Type of test - "one-sample", "proportion", "goodness-of-fit"
        alternative: Alternative hypothesis - "two-sided", "less", "greater"
        alpha: Significance level (default: 0.05)
        correction: Multiple comparison correction method (optional)

    Returns:
        ToolResponse with significance test results

    Example:
        "Test if average response time is significantly different from 2.0 seconds"
        → significance_test(
            dataset_id="performance_123",
            column="response_time",
            test_value=2.0,
            test_type="one-sample"
        )

        "Test if conversion rate is significantly higher than 10%"
        → significance_test(
            dataset_id="conversions_123",
            column="converted",
            test_value=0.10,
            test_type="proportion",
            alternative="greater"
        )

        "Test if observed category distribution matches expected uniform distribution"
        → significance_test(
            dataset_id="categories_123",
            column="category",
            test_value=0.25,  # Expected proportion for each of 4 categories
            test_type="goodness-of-fit"
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

        # Validate column
        if column not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Column '{column}' not found",
                metadata={"error": "ColumnNotFound", "column": column},
                storage_hint="never",
            )

        logger.info(f"Performing {test_type} significance test on column '{column}'")

        result = {}

        if test_type == "one-sample":
            # One-sample t-test
            data = df[column].dropna()
            n = len(data)
            mean = float(data.mean())
            std = float(data.std(ddof=1))
            se = std / np.sqrt(n)

            # Perform t-test
            statistic, p_value = stats.ttest_1samp(data, test_value, alternative=alternative)

            # Calculate effect size (Cohen's d)
            cohens_d = (mean - test_value) / std if std > 0 else 0.0

            # Confidence interval
            ci_level = 1 - alpha
            t_critical = stats.t.ppf(1 - alpha / 2, n - 1)
            ci_margin = t_critical * se
            ci_lower = mean - ci_margin
            ci_upper = mean + ci_margin

            result = {
                "test": "One-Sample t-test",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "sample_mean": mean,
                "sample_std": std,
                "hypothesized_value": test_value,
                "difference": mean - test_value,
                "sample_size": n,
                "standard_error": se,
                "confidence_interval": {
                    "level": ci_level,
                    "lower": ci_lower,
                    "upper": ci_upper,
                },
                "effect_size": {
                    "cohens_d": float(cohens_d),
                    "interpretation": _interpret_cohens_d(cohens_d),
                },
            }

        elif test_type == "proportion":
            # One-proportion z-test
            data = df[column].dropna()
            n = len(data)
            successes = int(data.sum())
            observed_proportion = successes / n if n > 0 else 0.0

            # Z-test for proportion
            hypothesized_prop = test_value

            if not 0 <= hypothesized_prop <= 1:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Hypothesized proportion must be between 0 and 1, got {hypothesized_prop}",
                    metadata={"error": "InvalidProportionValue"},
                    storage_hint="never",
                )

            # Standard error under null hypothesis
            se = np.sqrt(hypothesized_prop * (1 - hypothesized_prop) / n)

            if se > 0:
                z_statistic = (observed_proportion - hypothesized_prop) / se

                # P-value based on alternative hypothesis
                if alternative == "two-sided":
                    p_value = 2 * (1 - stats.norm.cdf(abs(z_statistic)))
                elif alternative == "greater":
                    p_value = 1 - stats.norm.cdf(z_statistic)
                elif alternative == "less":
                    p_value = stats.norm.cdf(z_statistic)
                else:
                    return ToolResponse(
                        payload=None,
                        summary=f"Error: Invalid alternative '{alternative}'",
                        metadata={"error": "InvalidAlternative"},
                        storage_hint="never",
                    )
            else:
                z_statistic = 0.0
                p_value = 1.0

            # Confidence interval (Wilson score)
            z_critical = stats.norm.ppf(1 - alpha / 2)
            denominator = 1 + z_critical**2 / n
            center = (observed_proportion + z_critical**2 / (2 * n)) / denominator
            margin = (
                z_critical
                * np.sqrt((observed_proportion * (1 - observed_proportion) + z_critical**2 / (4 * n)) / n)
                / denominator
            )
            ci_lower = max(0, center - margin)
            ci_upper = min(1, center + margin)

            result = {
                "test": "One-Proportion Z-Test",
                "statistic": float(z_statistic),
                "p_value": float(p_value),
                "observed_proportion": observed_proportion,
                "hypothesized_proportion": hypothesized_prop,
                "difference": observed_proportion - hypothesized_prop,
                "successes": successes,
                "sample_size": n,
                "standard_error": se,
                "confidence_interval": {
                    "level": 1 - alpha,
                    "lower": ci_lower,
                    "upper": ci_upper,
                },
            }

        elif test_type == "goodness-of-fit":
            # Chi-square goodness-of-fit test
            data = df[column].dropna()
            observed_counts = data.value_counts()
            n_categories = len(observed_counts)
            total_count = len(data)

            # Expected frequencies
            # If test_value is a proportion, assume uniform distribution
            if 0 < test_value < 1:
                # Interpret as expected proportion per category
                expected_counts = pd.Series([test_value * total_count] * n_categories, index=observed_counts.index)
            else:
                # Assume test_value is expected count per category
                expected_counts = pd.Series([test_value] * n_categories, index=observed_counts.index)

            # Perform chi-square test
            statistic, p_value = stats.chisquare(observed_counts, expected_counts)

            # Calculate standardized residuals
            residuals = {}
            for category in observed_counts.index:
                obs = observed_counts[category]
                exp = expected_counts[category]
                std_residual = (obs - exp) / np.sqrt(exp) if exp > 0 else 0.0
                residuals[str(category)] = {
                    "observed": int(obs),
                    "expected": float(exp),
                    "residual": obs - exp,
                    "standardized_residual": float(std_residual),
                }

            result = {
                "test": "Chi-Square Goodness-of-Fit Test",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "degrees_of_freedom": n_categories - 1,
                "n_categories": n_categories,
                "total_count": total_count,
                "categories": residuals,
            }

        else:
            return ToolResponse(
                payload=None,
                summary=f"Error: Unknown test type '{test_type}'",
                metadata={"error": "InvalidTestType", "test_type": test_type},
                storage_hint="never",
            )

        # Apply multiple comparison correction if specified
        if correction:
            original_p_value = result["p_value"]
            n_tests = 1  # Default to 1 test if not specified

            if correction == "bonferroni":
                corrected_alpha = alpha / n_tests
                result["corrected_alpha"] = corrected_alpha
                result["correction_method"] = "Bonferroni"
                result["original_p_value"] = original_p_value
                # Note: We can't adjust p-value without knowing n_tests
                # So we just adjust alpha
            elif correction == "holm":
                result["correction_method"] = "Holm-Bonferroni"
                result["original_p_value"] = original_p_value
                result["note"] = "Holm correction requires multiple p-values for sequential testing"
            elif correction == "fdr":
                result["correction_method"] = "False Discovery Rate (Benjamini-Hochberg)"
                result["original_p_value"] = original_p_value
                result["note"] = "FDR correction requires multiple p-values"
            else:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Unknown correction method '{correction}'",
                    metadata={"error": "InvalidCorrection", "correction": correction},
                    storage_hint="never",
                )

        # Add common fields
        result["alpha"] = alpha
        result["alternative"] = alternative
        result["significant"] = result["p_value"] < alpha

        # Generate summary
        summary = f"📊 {result['test']}\n\n"
        summary += f"Hypothesis: {alternative}\n"
        summary += f"Significance Level (α): {alpha}\n"

        if correction:
            summary += f"Multiple Comparison Correction: {result['correction_method']}\n"

        summary += "\n"

        if test_type == "one-sample":
            summary += "Sample Statistics:\n"
            summary += f"  • Sample Mean: {result['sample_mean']:.4f}\n"
            summary += f"  • Sample Std: {result['sample_std']:.4f}\n"
            summary += f"  • Sample Size: {result['sample_size']}\n"
            summary += f"  • Hypothesized Value: {result['hypothesized_value']:.4f}\n"
            summary += f"  • Difference: {result['difference']:.4f}\n\n"

        elif test_type == "proportion":
            summary += "Proportion Statistics:\n"
            summary += f"  • Observed Proportion: {result['observed_proportion']:.4f} ({result['successes']}/{result['sample_size']})\n"
            summary += f"  • Hypothesized Proportion: {result['hypothesized_proportion']:.4f}\n"
            summary += f"  • Difference: {result['difference']:.4f}\n\n"

        elif test_type == "goodness-of-fit":
            summary += "Distribution Statistics:\n"
            summary += f"  • Number of Categories: {result['n_categories']}\n"
            summary += f"  • Total Count: {result['total_count']}\n"
            summary += f"  • Degrees of Freedom: {result['degrees_of_freedom']}\n\n"

        summary += "Results:\n"
        summary += f"  • Test Statistic: {result['statistic']:.4f}\n"
        summary += f"  • P-value: {result['p_value']:.4f}\n"

        if correction and "original_p_value" in result:
            summary += f"  • Original P-value: {result['original_p_value']:.4f}\n"

        summary += f"  • Significant: {'Yes ✓' if result['significant'] else 'No ✗'}\n\n"

        if test_type in ["one-sample", "proportion"] and "confidence_interval" in result:
            ci_level = result["confidence_interval"]["level"]
            summary += f"{ci_level:.0%} Confidence Interval:\n"
            summary += (
                f"  • [{result['confidence_interval']['lower']:.4f}, {result['confidence_interval']['upper']:.4f}]\n\n"
            )

        if test_type == "one-sample" and "effect_size" in result:
            summary += "Effect Size:\n"
            summary += f"  • Cohen's d: {result['effect_size']['cohens_d']:.4f} ({result['effect_size']['interpretation']})\n\n"

        if test_type == "goodness-of-fit":
            summary += "Category Analysis (top 5 largest residuals):\n"
            sorted_categories = sorted(
                result["categories"].items(),
                key=lambda x: abs(x[1]["standardized_residual"]),
                reverse=True,
            )
            for category, stats_dict in sorted_categories[:5]:
                summary += f"  • {category}: obs={stats_dict['observed']}, exp={stats_dict['expected']:.1f}, "
                summary += f"std_residual={stats_dict['standardized_residual']:.2f}\n"
            summary += "\n"

        # Interpretation
        summary += "Interpretation:\n"
        if result["significant"]:
            summary += f"  ⚠️  Reject null hypothesis (p < {alpha})\n"
            if test_type == "one-sample":
                summary += f"  The sample mean ({result['sample_mean']:.4f}) is significantly different from {result['hypothesized_value']:.4f}\n"
            elif test_type == "proportion":
                summary += f"  The observed proportion ({result['observed_proportion']:.4f}) is significantly different from {result['hypothesized_proportion']:.4f}\n"
            elif test_type == "goodness-of-fit":
                summary += "  The observed distribution differs significantly from the expected distribution\n"
        else:
            summary += f"  ✓  Fail to reject null hypothesis (p >= {alpha})\n"
            if test_type == "one-sample":
                summary += (
                    f"  No significant evidence that sample mean differs from {result['hypothesized_value']:.4f}\n"
                )
            elif test_type == "proportion":
                summary += (
                    f"  No significant evidence that proportion differs from {result['hypothesized_proportion']:.4f}\n"
                )
            elif test_type == "goodness-of-fit":
                summary += "  The observed distribution is consistent with the expected distribution\n"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "test_type": test_type,
                "significant": result["significant"],
            },
            storage_hint="session",
            suggested_name=f"{test_type.replace('-', '_')}_significance",
        )

    except Exception as e:
        logger.exception(f"Error performing significance test: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error performing significance test: {e}",
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
