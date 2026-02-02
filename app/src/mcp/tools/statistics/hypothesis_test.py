"""Statistical hypothesis testing tools."""

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
async def hypothesis_test(
    dataset_id: str,
    test_type: str,
    column1: str,
    column2: str | None = None,
    group_column: str | None = None,
    alpha: float = 0.05,
    alternative: str = "two-sided",
) -> str:
    """Perform statistical hypothesis testing.

    Supports multiple test types:
    - t-test: Compare means of two groups (independent or paired)
    - chi-square: Test independence between categorical variables
    - anova: Compare means across multiple groups
    - mann-whitney: Non-parametric test for two independent samples
    - wilcoxon: Non-parametric test for paired samples
    - kruskal: Non-parametric alternative to ANOVA

    Args:
        dataset_id: Entity ID of the dataset
        test_type: Type of test - "t-test", "chi-square", "anova", "mann-whitney", "wilcoxon", "kruskal"
        column1: First column (or dependent variable for ANOVA)
        column2: Second column (optional, depends on test type)
        group_column: Column with group labels (for ANOVA/Kruskal)
        alpha: Significance level (default: 0.05)
        alternative: Alternative hypothesis - "two-sided", "less", "greater" (default: "two-sided")

    Returns:
        ToolResponse with test results

    Example:
        "Test if there's a significant difference in sales between regions"
        → hypothesis_test(
            dataset_id="sales_123",
            test_type="anova",
            column1="sales",
            group_column="region"
        )

        "Compare conversion rates using chi-square test"
        → hypothesis_test(
            dataset_id="users_123",
            test_type="chi-square",
            column1="treatment",
            column2="converted"
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
        if column1 not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Column '{column1}' not found",
                metadata={"error": "ColumnNotFound", "column": column1},
                storage_hint="never",
            )

        logger.info(f"Performing {test_type} test on dataset with {len(df)} rows")

        result = {}

        if test_type == "t-test":
            # Independent samples t-test
            if column2 is None:
                return ToolResponse(
                    payload=None,
                    summary="Error: t-test requires column2",
                    metadata={"error": "ValidationError"},
                    storage_hint="never",
                )

            if column2 not in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Column '{column2}' not found",
                    metadata={"error": "ColumnNotFound", "column": column2},
                    storage_hint="never",
                )

            data1 = df[column1].dropna()
            data2 = df[column2].dropna()

            statistic, p_value = stats.ttest_ind(data1, data2, alternative=alternative)

            result = {
                "test": "Independent Samples t-test",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "mean1": float(data1.mean()),
                "mean2": float(data2.mean()),
                "std1": float(data1.std()),
                "std2": float(data2.std()),
                "n1": len(data1),
                "n2": len(data2),
                "mean_diff": float(data1.mean() - data2.mean()),
            }

        elif test_type == "chi-square":
            # Chi-square test of independence
            if column2 is None:
                return ToolResponse(
                    payload=None,
                    summary="Error: chi-square test requires column2",
                    metadata={"error": "ValidationError"},
                    storage_hint="never",
                )

            if column2 not in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Column '{column2}' not found",
                    metadata={"error": "ColumnNotFound", "column": column2},
                    storage_hint="never",
                )

            # Create contingency table
            contingency_table = pd.crosstab(df[column1], df[column2])

            statistic, p_value, dof, expected = stats.chi2_contingency(contingency_table)

            result = {
                "test": "Chi-Square Test of Independence",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "degrees_of_freedom": int(dof),
                "contingency_table": contingency_table.to_dict(),
                "expected_frequencies": expected.tolist(),
            }

        elif test_type == "anova":
            # One-way ANOVA
            if group_column is None:
                return ToolResponse(
                    payload=None,
                    summary="Error: ANOVA requires group_column",
                    metadata={"error": "ValidationError"},
                    storage_hint="never",
                )

            if group_column not in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Column '{group_column}' not found",
                    metadata={"error": "ColumnNotFound", "column": group_column},
                    storage_hint="never",
                )

            # Group data
            groups = df.groupby(group_column)[column1].apply(lambda x: x.dropna().values).tolist()

            if len(groups) < 2:
                return ToolResponse(
                    payload=None,
                    summary="Error: ANOVA requires at least 2 groups",
                    metadata={"error": "ValidationError"},
                    storage_hint="never",
                )

            statistic, p_value = stats.f_oneway(*groups)

            group_stats = {}
            for group_name, group_data in df.groupby(group_column):
                group_vals = group_data[column1].dropna()
                group_stats[str(group_name)] = {
                    "mean": float(group_vals.mean()),
                    "std": float(group_vals.std()),
                    "count": len(group_vals),
                }

            result = {
                "test": "One-Way ANOVA",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "n_groups": len(groups),
                "group_stats": group_stats,
            }

        elif test_type == "mann-whitney":
            # Mann-Whitney U test (non-parametric alternative to t-test)
            if column2 is None:
                return ToolResponse(
                    payload=None,
                    summary="Error: Mann-Whitney test requires column2",
                    metadata={"error": "ValidationError"},
                    storage_hint="never",
                )

            if column2 not in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Column '{column2}' not found",
                    metadata={"error": "ColumnNotFound", "column": column2},
                    storage_hint="never",
                )

            data1 = df[column1].dropna()
            data2 = df[column2].dropna()

            statistic, p_value = stats.mannwhitneyu(data1, data2, alternative=alternative)

            result = {
                "test": "Mann-Whitney U Test",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "median1": float(data1.median()),
                "median2": float(data2.median()),
                "n1": len(data1),
                "n2": len(data2),
            }

        elif test_type == "wilcoxon":
            # Wilcoxon signed-rank test (paired non-parametric test)
            if column2 is None:
                return ToolResponse(
                    payload=None,
                    summary="Error: Wilcoxon test requires column2",
                    metadata={"error": "ValidationError"},
                    storage_hint="never",
                )

            if column2 not in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Column '{column2}' not found",
                    metadata={"error": "ColumnNotFound", "column": column2},
                    storage_hint="never",
                )

            data1 = df[column1].dropna()
            data2 = df[column2].dropna()

            # Align data (only compare where both have values)
            valid_idx = data1.index.intersection(data2.index)
            data1 = data1.loc[valid_idx]
            data2 = data2.loc[valid_idx]

            statistic, p_value = stats.wilcoxon(data1, data2, alternative=alternative)

            result = {
                "test": "Wilcoxon Signed-Rank Test",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "n_pairs": len(data1),
            }

        elif test_type == "kruskal":
            # Kruskal-Wallis H test (non-parametric alternative to ANOVA)
            if group_column is None:
                return ToolResponse(
                    payload=None,
                    summary="Error: Kruskal-Wallis test requires group_column",
                    metadata={"error": "ValidationError"},
                    storage_hint="never",
                )

            if group_column not in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Column '{group_column}' not found",
                    metadata={"error": "ColumnNotFound", "column": group_column},
                    storage_hint="never",
                )

            # Group data
            groups = df.groupby(group_column)[column1].apply(lambda x: x.dropna().values).tolist()

            if len(groups) < 2:
                return ToolResponse(
                    payload=None,
                    summary="Error: Kruskal-Wallis test requires at least 2 groups",
                    metadata={"error": "ValidationError"},
                    storage_hint="never",
                )

            statistic, p_value = stats.kruskal(*groups)

            group_stats = {}
            for group_name, group_data in df.groupby(group_column):
                group_vals = group_data[column1].dropna()
                group_stats[str(group_name)] = {
                    "median": float(group_vals.median()),
                    "count": len(group_vals),
                }

            result = {
                "test": "Kruskal-Wallis H Test",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "n_groups": len(groups),
                "group_stats": group_stats,
            }

        else:
            return ToolResponse(
                payload=None,
                summary=f"Error: Unknown test type '{test_type}'",
                metadata={"error": "InvalidTestType", "test_type": test_type},
                storage_hint="never",
            )

        # Add common fields
        result["alpha"] = alpha
        result["alternative"] = alternative
        result["significant"] = result["p_value"] < alpha

        # Generate summary
        summary = f"📊 {result['test']}\n\n"
        summary += f"Hypothesis: {alternative}\n"
        summary += f"Significance Level (α): {alpha}\n\n"

        summary += "Results:\n"
        summary += f"  • Test Statistic: {result['statistic']:.4f}\n"
        summary += f"  • P-value: {result['p_value']:.4f}\n"
        summary += f"  • Significant: {'Yes ✓' if result['significant'] else 'No ✗'}\n\n"

        # Test-specific details
        if test_type == "t-test" or test_type == "mann-whitney":
            summary += "Group Comparison:\n"
            if "mean1" in result:
                summary += f"  • Group 1: mean={result['mean1']:.4f}, std={result['std1']:.4f}, n={result['n1']}\n"
                summary += f"  • Group 2: mean={result['mean2']:.4f}, std={result['std2']:.4f}, n={result['n2']}\n"
                summary += f"  • Difference: {result['mean_diff']:.4f}\n"
            else:
                summary += f"  • Group 1: median={result['median1']:.4f}, n={result['n1']}\n"
                summary += f"  • Group 2: median={result['median2']:.4f}, n={result['n2']}\n"

        elif test_type in ["anova", "kruskal"]:
            summary += f"Groups ({result['n_groups']}):\n"
            for group_name, stats_dict in result.get("group_stats", {}).items():
                if "mean" in stats_dict:
                    summary += f"  • {group_name}: mean={stats_dict['mean']:.4f}, std={stats_dict['std']:.4f}, n={stats_dict['count']}\n"
                else:
                    summary += f"  • {group_name}: median={stats_dict['median']:.4f}, n={stats_dict['count']}\n"

        # Interpretation
        summary += "\nInterpretation:\n"
        if result["significant"]:
            summary += f"  ⚠️  Reject null hypothesis (p < {alpha})\n"
            summary += "  The observed difference is statistically significant.\n"
        else:
            summary += f"  ✓  Fail to reject null hypothesis (p >= {alpha})\n"
            summary += "  No statistically significant difference detected.\n"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "test_type": test_type,
                "significant": result["significant"],
            },
            storage_hint="session",
            suggested_name=f"{test_type.replace('-', '_')}_test",
        )

    except Exception as e:
        logger.exception(f"Error performing hypothesis test: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error performing hypothesis test: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )
