"""EDA API routes — Trigger and retrieve exploratory data analysis."""
import json
import pandas as pd
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Dataset, User
from app.api.deps import get_current_user
from app.services.profiler import DatasetProfiler
from app.services.insight_service import InsightService
from app.schemas.dataset import EDAResponse
from ml_engine.analysis.eda_engine import EDAEngine

router = APIRouter(prefix="/datasets", tags=["EDA"])


@router.post("/{dataset_id}/eda", response_model=EDAResponse)
def run_eda(
    dataset_id: str,
    target: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate EDA report with real statistics from the dataset and auto-generate insights."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    # Use cached EDA if target hasn't changed
    if dataset.eda_data and not target:
        try:
            cached = json.loads(dataset.eda_data)
            cached["dataset_id"] = dataset_id
            # Ensure insights exist
            InsightService.get_insights(dataset_id, db)
            return cached
        except Exception:
            pass

    df = DatasetProfiler.load_dataset(dataset.file_path)
    effective_target = target or dataset.target_column
    eda_results = EDAEngine.run_full_eda(df, target=effective_target)
    eda_results["dataset_id"] = dataset_id

    # Cache EDA
    dataset.eda_data = json.dumps(eda_results)
    if effective_target:
        dataset.target_column = effective_target
    db.commit()

    # Generate actionable auto-insights
    try:
        InsightService.generate_insights(dataset_id, eda_results, db)
    except Exception as e:
        pass

    return eda_results


@router.get("/{dataset_id}/insights")
def get_dataset_insights(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all automated quality and statistical insights for a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    insights = InsightService.get_insights(dataset_id, db)
    # If no insights yet and eda_data exists, generate now
    if not insights and dataset.eda_data:
        try:
            eda_data = json.loads(dataset.eda_data)
            insights = InsightService.generate_insights(dataset_id, eda_data, db)
        except Exception:
            pass

    return {"dataset_id": dataset_id, "insights": insights, "count": len(insights)}


@router.get("/{dataset_id}/statistical-tests")
def run_statistical_tests(
    dataset_id: str,
    target: Optional[str] = None,
    column_a: Optional[str] = None,
    column_b: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run rigorous inferential hypothesis tests (t-test, ANOVA, Chi-squared, correlation, normality)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    from ml_engine.analysis.statistical_engine import StatisticalEngine
    file_path = dataset.cleaned_file_path or dataset.file_path
    df = DatasetProfiler.load_dataset(file_path)

    # 1. Pairwise test if both column_a and column_b specified
    if column_a and column_b:
        if column_a not in df.columns or column_b not in df.columns:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specified columns not found in dataset.")

        import pandas as pd
        is_a_num = pd.api.types.is_numeric_dtype(df[column_a]) and df[column_a].nunique() > 5
        is_b_num = pd.api.types.is_numeric_dtype(df[column_b]) and df[column_b].nunique() > 5

        if is_a_num and is_b_num:
            result = StatisticalEngine.test_numerical_vs_numerical(df[column_a], df[column_b])
        elif is_a_num and not is_b_num:
            result = StatisticalEngine.test_numerical_vs_categorical(df[column_a], df[column_b])
        elif not is_a_num and is_b_num:
            result = StatisticalEngine.test_numerical_vs_categorical(df[column_b], df[column_a])
        else:
            result = StatisticalEngine.test_categorical_vs_categorical(df[column_a], df[column_b])

        result["column_a"] = column_a
        result["column_b"] = column_b
        return result

    # 2. Single column normality if only column_a specified
    if column_a and not column_b:
        if column_a not in df.columns:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Column '{column_a}' not found.")
        return StatisticalEngine.test_normality(df[column_a])

    # 3. Target hypothesis battery across all features
    effective_target = target or dataset.target_column
    if not effective_target or effective_target not in df.columns:
        # Pick last column as default target if none given
        effective_target = df.columns[-1]

    battery = StatisticalEngine.run_target_hypothesis_battery(df, effective_target)

    # Add normality checks for all numerical features
    import numpy as np
    num_cols = df.select_dtypes(include=[np.number]).columns[:15]
    normality_results = [StatisticalEngine.test_normality(df[c]) for c in num_cols]

    return {
        "dataset_id": dataset_id,
        "target_column": effective_target,
        "hypothesis_battery": battery,
        "normality_tests": normality_results,
    }


@router.get("/{dataset_id}/chart-recommendation")
def get_chart_recommendation(
    dataset_id: str,
    column_a: str,
    column_b: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get smart chart visualization recommendation for specific variable(s)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    from ml_engine.analysis.statistical_engine import StatisticalEngine
    file_path = dataset.cleaned_file_path or dataset.file_path
    df = DatasetProfiler.load_dataset(file_path)

    return StatisticalEngine.recommend_charts(df, column_a, column_b)


@router.get("/{dataset_id}/auto-eda-report")
def get_auto_eda_report(
    dataset_id: str,
    target: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate comprehensive, publication-ready Auto-EDA narrative report."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    from ml_engine.analysis.statistical_engine import StatisticalEngine
    file_path = dataset.cleaned_file_path or dataset.file_path
    df = DatasetProfiler.load_dataset(file_path)

    effective_target = target or dataset.target_column or df.columns[-1]
    eda = EDAEngine.run_full_eda(df, target=effective_target)
    battery = StatisticalEngine.run_target_hypothesis_battery(df, effective_target)

    # Format Markdown Report
    rows, cols = df.shape
    top_sig = [t["feature"] for t in battery.get("tests", []) if t.get("is_significant")][:4]

    md = f"""# Comprehensive Automated EDA Report
**Dataset:** `{dataset.original_filename}`  
**Dimensions:** {rows:,} rows × {cols} columns  
**Target Variable:** `{effective_target}`  
**Generated At:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  

---

## 1. Executive Summary & Findings
{battery.get('executive_narrative', 'Exploratory data analysis completed.')}

- **Total Features Analyzed:** {battery.get('total_tested', 0)}
- **Statistically Significant Predictors (p < 0.05):** {battery.get('significant_features_count', 0)}
- **Top Significant Drivers:** {', '.join(top_sig) if top_sig else 'None'}

---

## 2. Statistical Significance Leaderboard
| Feature | Type | Statistical Test | Statistic | p-value | Significant | Effect Size |
|---|---|---|---|---|---|---|
"""
    for t in battery.get("tests", [])[:12]:
        p_str = "< 0.001" if t['p_value'] is not None and t['p_value'] < 0.001 else f"{t['p_value']:.4f}" if t['p_value'] is not None else "N/A"
        md += f"| **{t['feature']}** | {t['feature_type']} | {t['test_name']} | {t['statistic']} | {p_str} | {'✅ Yes' if t['is_significant'] else '❌ No'} | {t['effect_size']} |\n"

    md += """
---

## 3. Modeling Readiness & Recommended Next Steps
1. **Feature Prioritization:** Anchor initial baseline models on the statistically validated drivers identified above.
2. **Pre-processing:** Impute missing cells and scale continuous features displaying skewness.
3. **Automated ML Pipeline:** Launch an AutoML experiment targeting `{effective_target}` using 5-fold cross-validation.
"""

    return {
        "dataset_id": dataset_id,
        "target_column": effective_target,
        "markdown_report": md,
        "summary": {
            "total_rows": rows,
            "total_columns": cols,
            "significant_features": battery.get("significant_features_count", 0),
            "top_drivers": top_sig,
        },
        "eda_stats": eda,
        "hypothesis_battery": battery,
    }

