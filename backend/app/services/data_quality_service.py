"""
Data Quality Engine v2 — Deep anomaly detection, target leakage,
fuzzy categorical inconsistencies, missingness patterns, multi-strategy outliers,
and comprehensive health scoring (0-100).
"""
import os
import json
import difflib
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models import Dataset, DataQualityReport, DatasetVersion
from app.services.profiler import DatasetProfiler


class DataQualityService:
    """Enterprise Data Quality Engine v2."""

    @staticmethod
    def assess_dataset(
        df: pd.DataFrame,
        target_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive data quality assessment across 5 core dimensions."""
        rows, cols = df.shape
        total_cells = max(rows * cols, 1)

        # 1. Missingness & Missing Patterns
        missingness = DataQualityService._analyze_missingness(df)

        # 2. Target Leakage (if target given or auto-detected)
        leakage = DataQualityService._detect_target_leakage(df, target_column)

        # 3. Fuzzy Categorical Inconsistencies
        fuzzy_inconsistencies = DataQualityService._detect_fuzzy_categories(df)

        # 4. Multi-Strategy Outliers
        outliers = DataQualityService._detect_outliers(df)

        # 5. Type Mismatches & Semantic Invalidity
        invalidity = DataQualityService._detect_invalidity(df)

        # 6. Duplicates
        duplicates_count = int(df.duplicated().sum())
        duplicates_pct = round((duplicates_count / max(rows, 1)) * 100, 2)

        # 7. Quality Scores (0 - 100)
        scores = DataQualityService._calculate_scores(
            rows=rows,
            cols=cols,
            total_cells=total_cells,
            missingness=missingness,
            duplicates_count=duplicates_count,
            fuzzy_inconsistencies=fuzzy_inconsistencies,
            outliers=outliers,
            invalidity=invalidity,
            leakage=leakage,
        )

        # 8. Actionable Remediation Recommendations
        recommendations = DataQualityService._generate_recommendations(
            missingness=missingness,
            leakage=leakage,
            fuzzy_inconsistencies=fuzzy_inconsistencies,
            outliers=outliers,
            invalidity=invalidity,
            duplicates_count=duplicates_count,
        )

        return {
            "overall_score": scores["overall_score"],
            "dimension_scores": scores,
            "dimensions": {
                "completeness": {
                    "score": scores["completeness_score"],
                    "total_missing": missingness["total_missing"],
                    "missing_percentage": missingness["missing_pct"],
                    "pattern": missingness["pattern_type"],
                    "columns_with_missing": missingness["columns"],
                },
                "validity": {
                    "score": scores["validity_score"],
                    "sentinel_values_count": invalidity["sentinel_total"],
                    "semantic_violations_count": invalidity["violation_total"],
                    "issues": invalidity["details"],
                },
                "uniqueness": {
                    "score": scores["uniqueness_score"],
                    "duplicate_rows": duplicates_count,
                    "duplicate_percentage": duplicates_pct,
                },
                "consistency": {
                    "score": scores["consistency_score"],
                    "inconsistent_categories": fuzzy_inconsistencies["total_clusters"],
                    "details": fuzzy_inconsistencies["columns"],
                },
                "leakage_risk": {
                    "score": scores["leakage_score"],
                    "target_column": target_column,
                    "high_risk_columns": leakage["high_risk_columns"],
                    "medium_risk_columns": leakage["medium_risk_columns"],
                    "details": leakage["details"],
                },
                "outliers": {
                    "total_outliers_detected": outliers["total_outliers"],
                    "columns": outliers["columns"],
                },
            },
            "recommendations": recommendations,
            "summary_stats": {
                "total_rows": rows,
                "total_columns": cols,
                "total_cells": total_cells,
                "assessed_at": pd.Timestamp.now().isoformat(),
            },
        }

    # ─── Missingness Patterns ─────────────────────────────────────────

    @staticmethod
    def _analyze_missingness(df: pd.DataFrame) -> Dict[str, Any]:
        rows, cols = df.shape
        missing_per_col = df.isna().sum()
        total_missing = int(missing_per_col.sum())
        total_cells = max(rows * cols, 1)
        missing_pct = round((total_missing / total_cells) * 100, 2)

        col_details = []
        missing_cols = []
        for col in df.columns:
            cnt = int(missing_per_col[col])
            if cnt > 0:
                missing_cols.append(col)
                col_details.append({
                    "column": col,
                    "count": cnt,
                    "percentage": round((cnt / max(rows, 1)) * 100, 2),
                })

        # Pattern diagnostic heuristic (MCAR vs MAR vs MNAR)
        pattern_type = "Complete"
        if total_missing > 0:
            if len(missing_cols) == 1:
                # Single column missingness
                pct = col_details[0]["percentage"]
                pattern_type = "MCAR (Single column low)" if pct < 10 else "MNAR (Clustered variable)"
            elif len(missing_cols) > 1:
                # Check correlation of missing indicator
                try:
                    missing_indicators = df[missing_cols].isna().astype(int)
                    corr = missing_indicators.corr().abs().values
                    np.fill_diagonal(corr, 0)
                    max_corr = np.nanmax(corr) if corr.size > 0 else 0
                    if max_corr > 0.4:
                        pattern_type = "MAR (Co-occurring missingness across features)"
                    elif missing_pct < 5.0:
                        pattern_type = "MCAR (Random low-frequency missingness)"
                    else:
                        pattern_type = "MNAR (Systematic missingness)"
                except Exception:
                    pattern_type = "MAR"
            else:
                pattern_type = "MCAR"

        return {
            "total_missing": total_missing,
            "missing_pct": missing_pct,
            "pattern_type": pattern_type,
            "columns": sorted(col_details, key=lambda x: x["percentage"], reverse=True),
        }

    # ─── Target Leakage ───────────────────────────────────────────────

    @staticmethod
    def _detect_target_leakage(df: pd.DataFrame, target_column: Optional[str]) -> Dict[str, Any]:
        if not target_column or target_column not in df.columns:
            return {
                "high_risk_columns": [],
                "medium_risk_columns": [],
                "details": [],
            }

        target_series = df[target_column]
        high_risk = []
        medium_risk = []
        details = []

        is_target_numeric = pd.api.types.is_numeric_dtype(target_series)

        for col in df.columns:
            if col == target_column:
                continue

            series = df[col]
            score = 0.0
            method = "none"

            try:
                if is_target_numeric and pd.api.types.is_numeric_dtype(series):
                    # Pearson correlation
                    valid_mask = series.notna() & target_series.notna()
                    if valid_mask.sum() > 10:
                        corr = np.abs(np.corrcoef(series[valid_mask], target_series[valid_mask])[0, 1])
                        if not np.isnan(corr):
                            score = float(corr)
                            method = "Pearson Correlation"
                else:
                    # Categorical / discrete correlation via contingency table / Cramér's V
                    valid_mask = series.notna() & target_series.notna()
                    if valid_mask.sum() > 10:
                        contingency = pd.crosstab(series[valid_mask], target_series[valid_mask])
                        if contingency.size > 1 and contingency.shape[0] > 1 and contingency.shape[1] > 1:
                            # Simplified Chi2 heuristic
                            chi2 = ((contingency - contingency.mean().mean()) ** 2).sum().sum()
                            n = valid_mask.sum()
                            score = float(min(np.sqrt(chi2 / (n * max(min(contingency.shape) - 1, 1))), 1.0))
                            method = "Association Index"
            except Exception:
                pass

            # Also check if column name sounds like future outcome or leakage
            col_lower = col.lower()
            suspicious_keywords = ["future", "next", "outcome", "result", "target", "label", "churned", "post_"]
            name_suspicious = any(kw in col_lower for kw in suspicious_keywords)

            risk_level = "low"
            if score >= 0.92 or (score >= 0.85 and name_suspicious):
                risk_level = "high"
                high_risk.append(col)
            elif score >= 0.80 or name_suspicious:
                risk_level = "medium"
                medium_risk.append(col)

            if risk_level in ("high", "medium"):
                details.append({
                    "column": col,
                    "risk_level": risk_level,
                    "association_score": round(score, 4),
                    "detection_method": method,
                    "reason": f"Very high association ({round(score * 100, 1)}%) with target column '{target_column}'",
                })

        return {
            "high_risk_columns": high_risk,
            "medium_risk_columns": medium_risk,
            "details": details,
        }

    # ─── Fuzzy Categorical Inconsistencies ────────────────────────────

    @staticmethod
    def _detect_fuzzy_categories(df: pd.DataFrame) -> Dict[str, Any]:
        columns_inconsistent = []
        total_clusters = 0

        for col in df.columns:
            series = df[col].dropna()
            if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
                continue

            unique_vals = [str(v).strip() for v in series.unique() if str(v).strip()]
            # Only analyze categorical features with reasonable cardinality (3 to 150)
            if len(unique_vals) < 2 or len(unique_vals) > 150:
                continue

            clusters = []
            seen = set()

            for i in range(len(unique_vals)):
                v1 = unique_vals[i]
                if v1.lower() in seen:
                    continue

                cluster = [v1]
                for j in range(i + 1, len(unique_vals)):
                    v2 = unique_vals[j]
                    if v2.lower() in seen:
                        continue

                    # Check 1: Case difference only
                    if v1.lower() == v2.lower():
                        cluster.append(v2)
                    else:
                        # Check 2: Fuzzy similarity > 0.84
                        ratio = difflib.SequenceMatcher(None, v1.lower(), v2.lower()).ratio()
                        if ratio >= 0.84 and len(v1) > 3 and len(v2) > 3:
                            cluster.append(v2)

                if len(cluster) > 1:
                    for v in cluster:
                        seen.add(v.lower())
                    clusters.append({
                        "canonical_suggestion": max(cluster, key=len),
                        "variants": cluster,
                    })

            if clusters:
                total_clusters += len(clusters)
                columns_inconsistent.append({
                    "column": col,
                    "unique_values_count": len(unique_vals),
                    "inconsistency_clusters": clusters,
                })

        return {
            "total_clusters": total_clusters,
            "columns": columns_inconsistent,
        }

    # ─── Multi-Strategy Outliers ──────────────────────────────────────

    @staticmethod
    def _detect_outliers(df: pd.DataFrame) -> Dict[str, Any]:
        outlier_cols = []
        total_outliers = 0

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 10:
                continue

            # Skip ID-like columns or binary 0/1
            if series.nunique() <= 2:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1

            if iqr <= 0:
                continue

            lower_iqr = q1 - 1.5 * iqr
            upper_iqr = q3 + 1.5 * iqr

            mean = float(series.mean())
            std = float(series.std())
            if std > 0:
                z_scores = np.abs((series - mean) / std)
                z_outliers_count = int((z_scores > 3.0).sum())
            else:
                z_outliers_count = 0

            iqr_mask = (series < lower_iqr) | (series > upper_iqr)
            iqr_count = int(iqr_mask.sum())

            if iqr_count > 0 or z_outliers_count > 0:
                pct = round((iqr_count / len(series)) * 100, 2)
                total_outliers += iqr_count
                outlier_cols.append({
                    "column": col,
                    "iqr_outliers": iqr_count,
                    "zscore_outliers": z_outliers_count,
                    "percentage": pct,
                    "lower_bound": round(lower_iqr, 3),
                    "upper_bound": round(upper_iqr, 3),
                    "min": round(float(series.min()), 3),
                    "max": round(float(series.max()), 3),
                })

        return {
            "total_outliers": total_outliers,
            "columns": sorted(outlier_cols, key=lambda x: x["percentage"], reverse=True),
        }

    # ─── Type Mismatches & Semantic Invalidity ────────────────────────

    @staticmethod
    def _detect_invalidity(df: pd.DataFrame) -> Dict[str, Any]:
        issues = []
        sentinel_total = 0
        violation_total = 0

        sentinel_candidates = {-999, -9999, -1, 9999, 99999, 999}

        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            col_lower = col.lower()

            # 1. Check numeric sentinel values
            if pd.api.types.is_numeric_dtype(series):
                for sentinel in sentinel_candidates:
                    cnt = int((series == sentinel).sum())
                    if cnt > 0 and sentinel not in (0, 1):
                        sentinel_total += cnt
                        issues.append({
                            "column": col,
                            "issue_type": "Sentinel Value",
                            "count": cnt,
                            "description": f"Found {cnt} occurrences of suspicious sentinel value '{sentinel}'",
                            "severity": "medium",
                        })

                # 2. Check semantic invalidities (e.g. Negative Age)
                if any(w in col_lower for w in ["age", "years_old"]):
                    neg_cnt = int((series < 0).sum())
                    over_cnt = int((series > 125).sum())
                    if neg_cnt > 0 or over_cnt > 0:
                        cnt = neg_cnt + over_cnt
                        violation_total += cnt
                        issues.append({
                            "column": col,
                            "issue_type": "Semantic Range Violation",
                            "count": cnt,
                            "description": f"Found {neg_cnt} negative ages and {over_cnt} ages > 125",
                            "severity": "high",
                        })

                # Price, Salary, Quantity, Count cannot be negative
                if any(w in col_lower for w in ["price", "salary", "wage", "revenue", "count", "quantity", "amount", "balance"]):
                    neg_cnt = int((series < 0).sum())
                    if neg_cnt > 0:
                        violation_total += neg_cnt
                        issues.append({
                            "column": col,
                            "issue_type": "Negative Domain Value",
                            "count": neg_cnt,
                            "description": f"Found {neg_cnt} negative values in typically positive domain '{col}'",
                            "severity": "medium",
                        })

            # 3. Check for string nulls in object columns (e.g. 'N/A', 'null', 'nan', 'none', '?')
            if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
                str_series = series.astype(str).str.strip().str.lower()
                pseudo_nulls = {"n/a", "null", "none", "nan", "undefined", "?", "-", "."}
                mask = str_series.isin(pseudo_nulls)
                pseudo_count = int(mask.sum())
                if pseudo_count > 0:
                    sentinel_total += pseudo_count
                    issues.append({
                        "column": col,
                        "issue_type": "Unparsed Pseudo-Null",
                        "count": pseudo_count,
                        "description": f"Found {pseudo_count} text-based null placeholders (e.g. 'N/A', 'none', '?')",
                        "severity": "low",
                    })

        return {
            "sentinel_total": sentinel_total,
            "violation_total": violation_total,
            "details": issues,
        }

    # ─── Scoring Engine ───────────────────────────────────────────────

    @staticmethod
    def _calculate_scores(
        rows: int,
        cols: int,
        total_cells: int,
        missingness: Dict[str, Any],
        duplicates_count: int,
        fuzzy_inconsistencies: Dict[str, Any],
        outliers: Dict[str, Any],
        invalidity: Dict[str, Any],
        leakage: Dict[str, Any],
    ) -> Dict[str, float]:
        # 1. Completeness Score (100 - missing percentage)
        completeness = max(0.0, min(100.0, 100.0 - missingness["missing_pct"]))

        # 2. Uniqueness Score (100 - duplicate percentage)
        dup_pct = (duplicates_count / max(rows, 1)) * 100
        uniqueness = max(0.0, min(100.0, 100.0 - (dup_pct * 1.5)))

        # 3. Validity Score (100 - sentinels & violations penalty)
        invalid_ratio = (invalidity["sentinel_total"] + invalidity["violation_total"]) / max(total_cells, 1)
        validity = max(0.0, min(100.0, 100.0 - (invalid_ratio * 100 * 5)))

        # 4. Consistency Score (100 - fuzzy clusters penalty)
        cluster_count = fuzzy_inconsistencies["total_clusters"]
        consistency = max(0.0, min(100.0, 100.0 - (cluster_count * 5.0)))

        # 5. Leakage Score
        high_leaks = len(leakage.get("high_risk_columns", []))
        med_leaks = len(leakage.get("medium_risk_columns", []))
        leakage_score = max(0.0, min(100.0, 100.0 - (high_leaks * 30.0 + med_leaks * 15.0)))

        # Overall weighted score
        overall = (
            completeness * 0.25 +
            validity * 0.25 +
            uniqueness * 0.20 +
            consistency * 0.15 +
            leakage_score * 0.15
        )

        return {
            "overall_score": round(float(overall), 1),
            "completeness_score": round(float(completeness), 1),
            "validity_score": round(float(validity), 1),
            "uniqueness_score": round(float(uniqueness), 1),
            "consistency_score": round(float(consistency), 1),
            "leakage_score": round(float(leakage_score), 1),
        }

    # ─── Recommendations ──────────────────────────────────────────────

    @staticmethod
    def _generate_recommendations(
        missingness: Dict[str, Any],
        leakage: Dict[str, Any],
        fuzzy_inconsistencies: Dict[str, Any],
        outliers: Dict[str, Any],
        invalidity: Dict[str, Any],
        duplicates_count: int,
    ) -> List[Dict[str, Any]]:
        recs = []

        # Leakage
        for leak in leakage.get("details", []):
            recs.append({
                "category": "leakage",
                "priority": "HIGH" if leak["risk_level"] == "high" else "MEDIUM",
                "action": f"Remove high-leakage column '{leak['column']}'",
                "detail": f"Column '{leak['column']}' exhibits {round(leak['association_score'] * 100, 1)}% correlation with target, risking severe overfitting.",
                "column": leak["column"],
                "suggested_fix": "drop_column",
            })

        # Duplicates
        if duplicates_count > 0:
            recs.append({
                "category": "uniqueness",
                "priority": "HIGH",
                "action": f"Deduplicate {duplicates_count} identical row records",
                "detail": f"Dataset contains {duplicates_count} duplicate rows that skew statistical inference.",
                "suggested_fix": "remove_duplicates",
            })

        # Missing values
        for col_m in missingness.get("columns", [])[:4]:
            pct = col_m["percentage"]
            if pct > 60:
                recs.append({
                    "category": "completeness",
                    "priority": "MEDIUM",
                    "action": f"Drop sparse column '{col_m['column']}'",
                    "detail": f"{pct}% of values are missing. Column lacks sufficient density for modeling.",
                    "column": col_m["column"],
                    "suggested_fix": "drop_column",
                })
            else:
                recs.append({
                    "category": "completeness",
                    "priority": "MEDIUM",
                    "action": f"Impute missing values in '{col_m['column']}'",
                    "detail": f"{col_m['count']} rows ({pct}%) missing. Impute with median or mode.",
                    "column": col_m["column"],
                    "suggested_fix": "impute",
                })

        # Fuzzy inconsistencies
        for col_c in fuzzy_inconsistencies.get("columns", [])[:3]:
            for cl in col_c["inconsistency_clusters"][:2]:
                recs.append({
                    "category": "consistency",
                    "priority": "MEDIUM",
                    "action": f"Standardize '{col_c['column']}' categorical variants",
                    "detail": f"Merge variant spellings: {', '.join(cl['variants'])} into '{cl['canonical_suggestion']}'.",
                    "column": col_c["column"],
                    "suggested_fix": "fuzzy_standardize",
                })

        # Invalidity
        for inv in invalidity.get("details", [])[:3]:
            recs.append({
                "category": "validity",
                "priority": "HIGH" if inv["severity"] == "high" else "MEDIUM",
                "action": f"Remediate {inv['issue_type']} in '{inv['column']}'",
                "detail": inv["description"],
                "column": inv["column"],
                "suggested_fix": "clean_sentinels",
            })

        # Outliers
        for out in outliers.get("columns", [])[:3]:
            if out["percentage"] > 5.0:
                recs.append({
                    "category": "outliers",
                    "priority": "LOW",
                    "action": f"Winsorize outliers in '{out['column']}'",
                    "detail": f"{out['iqr_outliers']} values exceed 1.5*IQR boundaries [{out['lower_bound']}, {out['upper_bound']}].",
                    "column": out["column"],
                    "suggested_fix": "winsorize",
                })

        return recs

    # ─── Database Persistence ─────────────────────────────────────────

    @classmethod
    def run_assessment_for_dataset(
        cls,
        db: Session,
        dataset_id: str,
        user_id: str,
        target_column: Optional[str] = None,
    ) -> DataQualityReport:
        """Run full assessment on dataset and store/update DataQualityReport record."""
        dataset = db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.user_id == user_id,
        ).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        file_path = dataset.cleaned_file_path or dataset.file_path
        df = DatasetProfiler.load_dataset(file_path)

        target = target_column or dataset.target_column
        report_data = cls.assess_dataset(df, target_column=target)

        # Check existing report
        existing = db.query(DataQualityReport).filter(
            DataQualityReport.dataset_id == dataset_id,
        ).first()

        dim_scores = report_data["dimension_scores"]

        if existing:
            existing.overall_score = dim_scores["overall_score"]
            existing.completeness_score = dim_scores["completeness_score"]
            existing.validity_score = dim_scores["validity_score"]
            existing.uniqueness_score = dim_scores["uniqueness_score"]
            existing.consistency_score = dim_scores["consistency_score"]
            existing.leakage_score = dim_scores["leakage_score"]
            existing.summary = json.dumps(report_data["dimensions"])
            existing.details = json.dumps(report_data)
            existing.recommendations = json.dumps(report_data["recommendations"])
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated DataQualityReport for dataset {dataset_id} (Score: {existing.overall_score})")
            return existing

        new_report = DataQualityReport(
            dataset_id=dataset_id,
            overall_score=dim_scores["overall_score"],
            completeness_score=dim_scores["completeness_score"],
            validity_score=dim_scores["validity_score"],
            uniqueness_score=dim_scores["uniqueness_score"],
            consistency_score=dim_scores["consistency_score"],
            leakage_score=dim_scores["leakage_score"],
            summary=json.dumps(report_data["dimensions"]),
            details=json.dumps(report_data),
            recommendations=json.dumps(report_data["recommendations"]),
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        logger.info(f"Generated new DataQualityReport for dataset {dataset_id} (Score: {new_report.overall_score})")
        return new_report
