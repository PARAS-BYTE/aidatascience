"""
Statistical Analysis & Hypothesis Testing Engine — Rigorous inference,
normality diagnostics, t-test/ANOVA/Chi-squared/Kruskal-Wallis tests,
effect sizes (Cohen's d, Eta-squared, Cramer's V), and executive narrative generation.
"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


class StatisticalEngine:
    """Rigorous inferential statistics & hypothesis testing engine."""

    # ─── 1. Normality Testing ─────────────────────────────────────────

    @staticmethod
    def test_normality(series: pd.Series) -> Dict[str, Any]:
        """Test whether a numerical variable follows a normal distribution."""
        clean = series.dropna().astype(float)
        if len(clean) < 8:
            return {
                "column": series.name,
                "is_normal": False,
                "p_value": None,
                "statistic": None,
                "test_used": "Insufficient Data",
                "skewness": round(float(clean.skew()), 3) if len(clean) > 2 else 0.0,
                "kurtosis": round(float(clean.kurtosis()), 3) if len(clean) > 3 else 0.0,
                "interpretation": "Insufficient data points (minimum 8 required) for normality assessment.",
            }

        skew = float(clean.skew())
        kurt = float(clean.kurtosis())

        # Sample for Shapiro if large (limit 5000)
        sample = clean.sample(n=min(len(clean), 5000), random_state=42) if len(clean) > 5000 else clean

        try:
            stat, p_val = stats.shapiro(sample)
            test_used = "Shapiro-Wilk"
        except Exception:
            try:
                stat, p_val = stats.normaltest(clean)
                test_used = "D'Agostino's K-squared"
            except Exception:
                stat, p_val = 0.0, 1.0
                test_used = "Heuristic"

        is_normal = bool(p_val >= 0.05)

        if is_normal:
            interpretation = (
                f"Normally distributed (p = {round(p_val, 4)} >= 0.05). "
                f"Parametric methods (t-test, ANOVA, Pearson) are statistically valid."
            )
        else:
            skew_desc = "positively skewed (right tail)" if skew > 0.5 else ("negatively skewed (left tail)" if skew < -0.5 else "symmetrical but non-normal")
            interpretation = (
                f"Significantly deviates from a normal distribution (p = {round(p_val, 5)} < 0.05, {skew_desc}). "
                f"Non-parametric tests (Mann-Whitney, Kruskal-Wallis, Spearman) are recommended."
            )

        return {
            "column": series.name,
            "is_normal": is_normal,
            "p_value": round(float(p_val), 5),
            "statistic": round(float(stat), 4),
            "test_used": test_used,
            "skewness": round(skew, 3),
            "kurtosis": round(kurt, 3),
            "interpretation": interpretation,
        }

    # ─── 2. Numerical vs Categorical (2 Groups or 3+ Groups) ──────────

    @staticmethod
    def test_numerical_vs_categorical(
        series_num: pd.Series,
        series_cat: pd.Series,
    ) -> Dict[str, Any]:
        """Test whether a numerical variable differs significantly across categories."""
        df = pd.DataFrame({"num": series_num, "cat": series_cat}).dropna()
        if len(df) < 5:
            return {"error": "Insufficient observations after dropping nulls."}

        groups = [group["num"].values for _, group in df.groupby("cat")]
        group_names = [str(name) for name, _ in df.groupby("cat")]
        n_groups = len(groups)

        if n_groups < 2:
            return {"error": "Categorical feature must have at least 2 distinct groups."}

        # Check normality of largest group
        normality_p = StatisticalEngine.test_normality(df["num"])["p_value"] or 0.0
        use_parametric = normality_p >= 0.01

        if n_groups == 2:
            # 2 Groups: Welch's t-test + Mann-Whitney U test
            g1, g2 = groups[0], groups[1]
            n1, n2 = len(g1), len(g2)
            m1, m2 = float(np.mean(g1)), float(np.mean(g2))
            s1, s2 = float(np.std(g1, ddof=1)) if n1 > 1 else 0.0, float(np.std(g2, ddof=1)) if n2 > 1 else 0.0

            # Welch's t-test
            try:
                t_stat, t_pval = stats.ttest_ind(g1, g2, equal_var=False)
            except Exception:
                t_stat, t_pval = 0.0, 1.0

            # Mann-Whitney U test
            try:
                u_stat, u_pval = stats.mannwhitneyu(g1, g2, alternative="two-sided")
            except Exception:
                u_stat, u_pval = 0.0, 1.0

            # Cohen's d effect size
            pooled_sd = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / max(n1 + n2 - 2, 1))
            cohens_d = (m1 - m2) / pooled_sd if pooled_sd > 0 else 0.0

            abs_d = abs(cohens_d)
            if abs_d < 0.2:
                d_desc = "Negligible effect"
            elif abs_d < 0.5:
                d_desc = "Small effect"
            elif abs_d < 0.8:
                d_desc = "Medium effect"
            else:
                d_desc = "Large effect"

            p_val = float(t_pval if use_parametric else u_pval)
            stat_val = float(t_stat if use_parametric else u_stat)
            test_name = "Welch's Two-Sample t-test" if use_parametric else "Mann-Whitney U Test"

            diff = m1 - m2
            direction = f"Group '{group_names[0]}' is on average {abs(round(diff, 2))} units {'higher' if diff > 0 else 'lower'} than '{group_names[1]}'."

            sig_text = "statistically significant difference" if p_val < 0.05 else "no statistically significant difference"
            interpretation = (
                f"There is a {sig_text} in '{series_num.name}' between {group_names[0]} and {group_names[1]} "
                f"({test_name}: p = {round(p_val, 5)}, Cohen's d = {round(cohens_d, 3)} [{d_desc}]). {direction}"
            )

            return {
                "test_type": "two_sample_comparison",
                "test_name": test_name,
                "parametric": use_parametric,
                "statistic": round(stat_val, 4),
                "p_value": round(p_val, 5),
                "is_significant": bool(p_val < 0.05),
                "effect_size": {
                    "metric": "Cohen's d",
                    "value": round(float(cohens_d), 3),
                    "magnitude": d_desc,
                },
                "group_summaries": [
                    {"group": group_names[0], "count": n1, "mean": round(m1, 3), "std": round(s1, 3)},
                    {"group": group_names[1], "count": n2, "mean": round(m2, 3), "std": round(s2, 3)},
                ],
                "interpretation": interpretation,
            }

        else:
            # 3+ Groups: One-way ANOVA + Kruskal-Wallis
            try:
                f_stat, f_pval = stats.f_oneway(*groups)
            except Exception:
                f_stat, f_pval = 0.0, 1.0

            try:
                h_stat, h_pval = stats.kruskal(*groups)
            except Exception:
                h_stat, h_pval = 0.0, 1.0

            # Eta-squared effect size
            all_vals = np.concatenate(groups)
            grand_mean = np.mean(all_vals)
            ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in groups)
            ss_total = sum((x - grand_mean)**2 for x in all_vals)
            eta_squared = ss_between / ss_total if ss_total > 0 else 0.0

            if eta_squared < 0.01:
                eta_desc = "Negligible effect"
            elif eta_squared < 0.06:
                eta_desc = "Small effect"
            elif eta_squared < 0.14:
                eta_desc = "Medium effect"
            else:
                eta_desc = "Large effect"

            p_val = float(f_pval if use_parametric else h_pval)
            stat_val = float(f_stat if use_parametric else h_stat)
            test_name = "One-way ANOVA" if use_parametric else "Kruskal-Wallis H-test"

            sig_text = "significant variance" if p_val < 0.05 else "no significant variance"
            interpretation = (
                f"'{series_num.name}' shows {sig_text} across the {n_groups} categories of '{series_cat.name}' "
                f"({test_name}: p = {round(p_val, 5)}, Eta-squared = {round(eta_squared, 3)} [{eta_desc}])."
            )

            summaries = [
                {"group": str(name), "count": len(g), "mean": round(float(np.mean(g)), 3), "std": round(float(np.std(g, ddof=1)) if len(g) > 1 else 0.0, 3)}
                for name, g in zip(group_names[:8], groups[:8])
            ]

            return {
                "test_type": "multigroup_comparison",
                "test_name": test_name,
                "parametric": use_parametric,
                "statistic": round(stat_val, 4),
                "p_value": round(p_val, 5),
                "is_significant": bool(p_val < 0.05),
                "effect_size": {
                    "metric": "Eta-squared",
                    "value": round(float(eta_squared), 3),
                    "magnitude": eta_desc,
                },
                "group_summaries": summaries,
                "interpretation": interpretation,
            }

    # ─── 3. Categorical vs Categorical ────────────────────────────────

    @staticmethod
    def test_categorical_vs_categorical(
        series_cat1: pd.Series,
        series_cat2: pd.Series,
    ) -> Dict[str, Any]:
        """Pearson's Chi-squared test of independence + Cramer's V."""
        df = pd.DataFrame({"c1": series_cat1, "c2": series_cat2}).dropna()
        if len(df) < 5:
            return {"error": "Insufficient observations after dropping nulls."}

        contingency = pd.crosstab(df["c1"], df["c2"])
        if contingency.shape[0] < 2 or contingency.shape[1] < 2:
            return {"error": "Both categorical features must have at least 2 categories."}

        try:
            chi2, p_val, dof, expected = stats.chi2_contingency(contingency)
        except Exception as e:
            return {"error": f"Chi-squared calculation failed: {str(e)}"}

        # Cramer's V effect size
        n = df.shape[0]
        min_dim = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
        cramers_v = np.sqrt(chi2 / (n * max(min_dim, 1))) if min_dim > 0 and n > 0 else 0.0
        cramers_v = min(float(cramers_v), 1.0)

        if cramers_v < 0.1:
            v_desc = "Negligible association"
        elif cramers_v < 0.3:
            v_desc = "Weak association"
        elif cramers_v < 0.5:
            v_desc = "Moderate association"
        else:
            v_desc = "Strong association"

        sig_text = "statistically significant dependency" if p_val < 0.05 else "independent relationship (no significant association)"
        interpretation = (
            f"'{series_cat1.name}' and '{series_cat2.name}' demonstrate a {sig_text} "
            f"(Chi2 = {round(chi2, 2)}, p = {round(p_val, 5)}, Cramer's V = {round(cramers_v, 3)} [{v_desc}])."
        )

        # Convert top contingency cells to dict
        top_contingency = contingency.iloc[:6, :6].to_dict()

        return {
            "test_type": "chi_squared_independence",
            "test_name": "Pearson's Chi-squared Test",
            "statistic": round(float(chi2), 3),
            "p_value": round(float(p_val), 5),
            "degrees_of_freedom": int(dof),
            "is_significant": bool(p_val < 0.05),
            "effect_size": {
                "metric": "Cramer's V",
                "value": round(float(cramers_v), 3),
                "magnitude": v_desc,
            },
            "sample_size": n,
            "contingency_table": top_contingency,
            "interpretation": interpretation,
        }

    # ─── 4. Numerical vs Numerical Correlation with Significance ───────

    @staticmethod
    def test_numerical_vs_numerical(
        series_num1: pd.Series,
        series_num2: pd.Series,
    ) -> Dict[str, Any]:
        """Pearson, Spearman, and Kendall correlation with significance p-values."""
        df = pd.DataFrame({"x": series_num1, "y": series_num2}).dropna().astype(float)
        if len(df) < 5:
            return {"error": "Insufficient observations after dropping nulls."}

        x, y = df["x"], df["y"]

        try:
            pearson_r, pearson_p = stats.pearsonr(x, y)
        except Exception:
            pearson_r, pearson_p = 0.0, 1.0

        try:
            spearman_r, spearman_p = stats.spearmanr(x, y)
        except Exception:
            spearman_r, spearman_p = 0.0, 1.0

        try:
            kendall_tau, kendall_p = stats.kendalltau(x, y)
        except Exception:
            kendall_tau, kendall_p = 0.0, 1.0

        abs_r = abs(float(pearson_r))
        if abs_r < 0.2:
            r_desc = "Very weak / negligible"
        elif abs_r < 0.4:
            r_desc = "Weak"
        elif abs_r < 0.7:
            r_desc = "Moderate"
        else:
            r_desc = "Strong"

        direction = "positive" if pearson_r > 0 else "negative"
        sig_text = "statistically significant" if pearson_p < 0.05 else "not statistically significant"

        interpretation = (
            f"'{series_num1.name}' and '{series_num2.name}' exhibit a {sig_text}, {r_desc} {direction} correlation "
            f"(Pearson r = {round(pearson_r, 3)}, p = {round(pearson_p, 5)}; Spearman rho = {round(spearman_r, 3)}, p = {round(spearman_p, 5)})."
        )

        return {
            "test_type": "correlation_significance",
            "pearson": {
                "r": round(float(pearson_r), 4),
                "p_value": round(float(pearson_p), 5),
                "is_significant": bool(pearson_p < 0.05),
                "strength": r_desc,
            },
            "spearman": {
                "rho": round(float(spearman_r), 4),
                "p_value": round(float(spearman_p), 5),
                "is_significant": bool(spearman_p < 0.05),
            },
            "kendall": {
                "tau": round(float(kendall_tau), 4),
                "p_value": round(float(kendall_p), 5),
                "is_significant": bool(kendall_p < 0.05),
            },
            "sample_size": len(df),
            "interpretation": interpretation,
        }

    # ─── 5. Automated Target Hypothesis Battery ───────────────────────

    @classmethod
    def run_target_hypothesis_battery(
        cls,
        df: pd.DataFrame,
        target_column: str,
    ) -> Dict[str, Any]:
        """Run statistical significance tests for every feature against target."""
        if target_column not in df.columns:
            return {"error": f"Target '{target_column}' not found."}

        target_series = df[target_column]
        is_target_numeric = pd.api.types.is_numeric_dtype(target_series) and target_series.nunique() > 5

        results = []

        for col in df.columns:
            if col == target_column:
                continue

            series = df[col]
            is_col_numeric = pd.api.types.is_numeric_dtype(series) and series.nunique() > 5

            try:
                if is_target_numeric and is_col_numeric:
                    # Num vs Num
                    res = cls.test_numerical_vs_numerical(series, target_series)
                    if "error" not in res:
                        results.append({
                            "feature": col,
                            "feature_type": "numerical",
                            "test_name": "Pearson / Spearman",
                            "statistic": res["pearson"]["r"],
                            "p_value": res["pearson"]["p_value"],
                            "is_significant": res["pearson"]["is_significant"],
                            "effect_size": res["pearson"]["strength"],
                            "interpretation": res["interpretation"],
                        })

                elif is_col_numeric and not is_target_numeric:
                    # Num vs Cat Target
                    res = cls.test_numerical_vs_categorical(series, target_series)
                    if "error" not in res:
                        results.append({
                            "feature": col,
                            "feature_type": "numerical",
                            "test_name": res["test_name"],
                            "statistic": res["statistic"],
                            "p_value": res["p_value"],
                            "is_significant": res["is_significant"],
                            "effect_size": f"{res['effect_size']['metric']}: {res['effect_size']['value']} ({res['effect_size']['magnitude']})",
                            "interpretation": res["interpretation"],
                        })

                elif not is_col_numeric and is_target_numeric:
                    # Cat vs Num Target
                    res = cls.test_numerical_vs_categorical(target_series, series)
                    if "error" not in res:
                        results.append({
                            "feature": col,
                            "feature_type": "categorical",
                            "test_name": res["test_name"],
                            "statistic": res["statistic"],
                            "p_value": res["p_value"],
                            "is_significant": res["is_significant"],
                            "effect_size": f"{res['effect_size']['metric']}: {res['effect_size']['value']} ({res['effect_size']['magnitude']})",
                            "interpretation": res["interpretation"],
                        })

                else:
                    # Cat vs Cat
                    res = cls.test_categorical_vs_categorical(series, target_series)
                    if "error" not in res:
                        results.append({
                            "feature": col,
                            "feature_type": "categorical",
                            "test_name": res["test_name"],
                            "statistic": res["statistic"],
                            "p_value": res["p_value"],
                            "is_significant": res["is_significant"],
                            "effect_size": f"{res['effect_size']['metric']}: {res['effect_size']['value']} ({res['effect_size']['magnitude']})",
                            "interpretation": res["interpretation"],
                        })
            except Exception as e:
                continue

        # Sort by p-value ascending (most significant first)
        results = sorted(results, key=lambda x: x["p_value"] if x["p_value"] is not None else 1.0)
        significant_count = sum(1 for r in results if r["is_significant"])

        # Generate Executive Narrative
        top_significant = [r["feature"] for r in results if r["is_significant"]][:3]
        if top_significant:
            narrative = (
                f"Statistical hypothesis testing confirmed {significant_count} out of {len(results)} features "
                f"have statistically significant relationships with target '{target_column}' (p < 0.05). "
                f"The strongest statistical drivers are: {', '.join(top_significant)}. "
                f"Features demonstrating no significant variance should be monitored or deprioritized during feature selection."
            )
        else:
            narrative = (
                f"Statistical hypothesis testing showed no individual features with p < 0.05 significance "
                f"against target '{target_column}'. Non-linear interaction features or non-parametric modeling may be necessary."
            )

        return {
            "target_column": target_column,
            "total_tested": len(results),
            "significant_features_count": significant_count,
            "executive_narrative": narrative,
            "tests": results,
        }

    # ─── 6. Smart Chart Recommender ───────────────────────────────────

    @staticmethod
    def recommend_charts(
        df: pd.DataFrame,
        column_a: str,
        column_b: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recommend best visualization types and parameters based on data typology."""
        if column_a not in df.columns:
            return {"error": f"Column '{column_a}' not found."}

        s_a = df[column_a].dropna()
        is_a_num = pd.api.types.is_numeric_dtype(s_a) and s_a.nunique() > 5

        if not column_b or column_b not in df.columns:
            # Single Variable
            if is_a_num:
                return {
                    "primary_chart": "histogram",
                    "secondary_chart": "box_plot",
                    "title": f"Distribution of {column_a}",
                    "explanation": "Numerical distribution best viewed as a binned frequency histogram with KDE curve and boxplot for outlier detection.",
                    "recommended_bins": min(30, max(10, int(np.sqrt(len(s_a))))),
                }
            else:
                cardinality = s_a.nunique()
                return {
                    "primary_chart": "bar_chart",
                    "secondary_chart": "donut_chart" if cardinality <= 6 else "horizontal_bar",
                    "title": f"Frequency Breakdown of {column_a}",
                    "explanation": f"Categorical feature with {cardinality} distinct classes. Bar chart provides optimal rank comparison.",
                }

        # Bivariate
        s_b = df[column_b].dropna()
        is_b_num = pd.api.types.is_numeric_dtype(s_b) and s_b.nunique() > 5

        if is_a_num and is_b_num:
            return {
                "primary_chart": "scatter_plot",
                "secondary_chart": "hexbin_density",
                "title": f"Bivariate Relationship: {column_a} vs {column_b}",
                "explanation": "Two continuous variables best analyzed with a scatter plot overlaying OLS linear trendline.",
            }
        elif is_a_num and not is_b_num:
            return {
                "primary_chart": "grouped_box_plot",
                "secondary_chart": "violin_plot",
                "title": f"Distribution of {column_a} Grouped by {column_b}",
                "explanation": "Continuous variable across discrete categories best evaluated with comparative boxplots showing median & quartiles.",
            }
        elif not is_a_num and is_b_num:
            return {
                "primary_chart": "grouped_box_plot",
                "secondary_chart": "horizontal_bar_means",
                "title": f"Distribution of {column_b} Grouped by {column_a}",
                "explanation": "Continuous variable across discrete categories best evaluated with comparative boxplots.",
            }
        else:
            return {
                "primary_chart": "stacked_bar_chart",
                "secondary_chart": "contingency_heatmap",
                "title": f"Cross-Tabulation: {column_a} and {column_b}",
                "explanation": "Two categorical variables best visualized with 100% normalized stacked bar chart or cross-tabulation heatmap.",
            }
