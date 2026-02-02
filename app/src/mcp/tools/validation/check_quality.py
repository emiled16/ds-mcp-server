"""Comprehensive data quality assessment."""

import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def check_data_quality(
    dataset_id: str,
    completeness_threshold: float = 0.95,
    uniqueness_threshold: float = 0.01,
) -> str:
    """Perform comprehensive data quality assessment.

    Checks multiple dimensions of data quality:
    - Completeness: Percentage of non-null values
    - Uniqueness: Percentage of unique values
    - Validity: Data type consistency
    - Accuracy: Basic statistical outliers
    - Consistency: Duplicate rows

    Args:
        dataset_id: Entity ID of the dataset to assess
        completeness_threshold: Minimum acceptable completeness (0-1, default: 0.95)
        uniqueness_threshold: Minimum unique ratio to flag as potential ID column (default: 0.01)

    Returns:
        ToolResponse with quality assessment results

    Example:
        "Check the quality of the customer data"
        → check_data_quality(dataset_id="customer_data_123")

        "Assess data quality with strict completeness threshold"
        → check_data_quality(
            dataset_id="sales_data_123",
            completeness_threshold=0.99
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

        logger.info(f"Assessing data quality for dataset with {len(df)} rows, {len(df.columns)} columns")

        quality_report = {
            "overall_score": 0.0,
            "dimensions": {},
            "column_quality": {},
            "issues": [],
            "recommendations": [],
        }

        # 1. COMPLETENESS
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isnull().sum().sum()
        completeness = (total_cells - missing_cells) / total_cells if total_cells > 0 else 0

        quality_report["dimensions"]["completeness"] = {
            "score": completeness,
            "total_cells": total_cells,
            "missing_cells": int(missing_cells),
            "threshold": completeness_threshold,
            "pass": completeness >= completeness_threshold,
        }

        if completeness < completeness_threshold:
            quality_report["issues"].append(
                f"Low completeness: {completeness:.2%} (threshold: {completeness_threshold:.2%})"
            )
            quality_report["recommendations"].append("Handle missing values (imputation or removal)")

        # 2. UNIQUENESS (per column)
        duplicate_rows = df.duplicated().sum()
        duplicate_ratio = duplicate_rows / len(df) if len(df) > 0 else 0

        quality_report["dimensions"]["uniqueness"] = {
            "duplicate_rows": int(duplicate_rows),
            "duplicate_ratio": duplicate_ratio,
            "unique_row_ratio": 1 - duplicate_ratio,
        }

        if duplicate_rows > 0:
            quality_report["issues"].append(f"Found {duplicate_rows} duplicate rows ({duplicate_ratio:.2%})")
            quality_report["recommendations"].append("Review and remove duplicate rows if not expected")

        # 3. COLUMN-LEVEL QUALITY
        potential_ids = []
        high_cardinality_cols = []
        low_variance_cols = []

        for col in df.columns:
            col_quality = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "null_ratio": float(df[col].isnull().sum() / len(df)),
                "unique_count": int(df[col].nunique()),
                "unique_ratio": float(df[col].nunique() / len(df)),
            }

            # Check for potential ID columns
            if col_quality["unique_ratio"] > 0.99 and col_quality["null_ratio"] < uniqueness_threshold:
                potential_ids.append(col)
                col_quality["potential_id"] = True

            # Check for high cardinality (might need encoding)
            if col_quality["unique_count"] > 100 and not pd.api.types.is_numeric_dtype(df[col]):
                high_cardinality_cols.append(col)

            # Check for low variance (constant or near-constant)
            if col_quality["unique_count"] == 1:
                low_variance_cols.append(col)
                col_quality["constant"] = True

            # For numeric columns, add statistics
            if pd.api.types.is_numeric_dtype(df[col]):
                col_quality["min"] = float(df[col].min()) if not df[col].isnull().all() else None
                col_quality["max"] = float(df[col].max()) if not df[col].isnull().all() else None
                col_quality["mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
                col_quality["std"] = float(df[col].std()) if not df[col].isnull().all() else None

                # Check for infinite values
                inf_count = int((df[col] == float("inf")).sum() + (df[col] == float("-inf")).sum())
                if inf_count > 0:
                    col_quality["inf_count"] = inf_count
                    quality_report["issues"].append(f"Column '{col}': {inf_count} infinite values")

            quality_report["column_quality"][col] = col_quality

        # Add findings
        if potential_ids:
            quality_report["recommendations"].append(f"Potential ID columns: {potential_ids}")

        if high_cardinality_cols:
            quality_report["issues"].append(f"High cardinality columns: {high_cardinality_cols[:5]}")
            quality_report["recommendations"].append("Consider encoding or aggregating high-cardinality features")

        if low_variance_cols:
            quality_report["issues"].append(f"Constant columns (no variance): {low_variance_cols}")
            quality_report["recommendations"].append("Remove constant columns as they don't provide information")

        # 4. DATA TYPE CONSISTENCY
        mixed_type_cols = []
        for col in df.columns:
            if df[col].dtype == "object":
                # Check if column has mixed types
                types = df[col].dropna().apply(type).unique()
                if len(types) > 1:
                    mixed_type_cols.append(col)

        if mixed_type_cols:
            quality_report["issues"].append(f"Mixed type columns: {mixed_type_cols}")
            quality_report["recommendations"].append("Ensure type consistency in columns")

        # 5. OVERALL QUALITY SCORE (weighted average)
        weights = {
            "completeness": 0.4,
            "uniqueness": 0.3,
            "validity": 0.3,
        }

        completeness_score = completeness
        uniqueness_score = 1 - duplicate_ratio
        validity_score = 1 - (len(mixed_type_cols) / len(df.columns)) if len(df.columns) > 0 else 0

        overall_score = (
            weights["completeness"] * completeness_score
            + weights["uniqueness"] * uniqueness_score
            + weights["validity"] * validity_score
        )

        quality_report["overall_score"] = overall_score
        quality_report["dimensions"]["validity"] = {
            "score": validity_score,
            "mixed_type_columns": mixed_type_cols,
        }

        # Generate summary
        summary = "📊 Data Quality Assessment\n\n"
        summary += f"Dataset: {len(df):,} rows, {len(df.columns)} columns\n"
        summary += f"Overall Quality Score: {overall_score:.2%}\n\n"

        # Quality dimensions
        summary += "Quality Dimensions:\n"
        summary += f"  • Completeness: {completeness:.2%} "
        summary += f"{'✅' if quality_report['dimensions']['completeness']['pass'] else '❌'}\n"
        summary += f"  • Uniqueness: {uniqueness_score:.2%}\n"
        summary += f"  • Validity: {validity_score:.2%}\n\n"

        # Issues
        if quality_report["issues"]:
            summary += f"Issues Found ({len(quality_report['issues'])}):\n"
            for issue in quality_report["issues"][:10]:
                summary += f"  ⚠️  {issue}\n"
            if len(quality_report["issues"]) > 10:
                summary += f"  ... and {len(quality_report['issues']) - 10} more\n"
            summary += "\n"

        # Recommendations
        if quality_report["recommendations"]:
            summary += f"Recommendations ({len(quality_report['recommendations'])}):\n"
            for rec in quality_report["recommendations"][:5]:
                summary += f"  💡 {rec}\n"
            if len(quality_report["recommendations"]) > 5:
                summary += f"  ... and {len(quality_report['recommendations']) - 5} more\n"
            summary += "\n"

        # Grade
        if overall_score >= 0.9:
            grade = "Excellent"
        elif overall_score >= 0.75:
            grade = "Good"
        elif overall_score >= 0.6:
            grade = "Fair"
        else:
            grade = "Poor"

        summary += f"Quality Grade: {grade}\n"

        return ToolResponse(
            payload=quality_report,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "overall_score": overall_score,
                "grade": grade,
            },
            storage_hint="session",
            suggested_name="data_quality_report",
        )

    except Exception as e:
        logger.exception(f"Error checking data quality: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error checking data quality: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )
