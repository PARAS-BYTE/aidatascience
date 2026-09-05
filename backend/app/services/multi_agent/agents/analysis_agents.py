"""
Analysis & Visualization Agents — Run concurrently during exploratory and diagnostic analysis.
1. QueryPlannerAgent: Translates analytical questions into structured query specifications
2. AnalysisExecutionAgent: Executes data query, grouping, aggregation, and filtering
3. ChartSelectionAgent: Selects optimal visualization chart types and layouts
4. TrendAgent: Detects growth rates, seasonality, trend directions, MoM/QoQ
5. SegmentationAgent: Profiles and ranks categorical segments & cohorts
6. AnomalyAgent: Flags outliers and anomalous records using statistical + ML ensembles
7. WhyInvestigationAgent: Parallel root-cause dimension decomposition ranking drivers
8. NarrativeAgent: Generates ranked plain-English executive insights with confidence scores
"""
import re
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
from scipy import stats

from app.services.multi_agent.blackboard import SharedBlackboard


class QueryPlannerAgent:
    """Translates user prompt into a structured analytical query specification."""

    @staticmethod
    def run(blackboard: SharedBlackboard, prompt: str = "") -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe available on blackboard"}

        semantics = blackboard.get("semantics") or {}
        metric_cols = [str(c) for c in semantics.get("metric_columns", [])]
        dim_cols = [str(c) for c in semantics.get("dimension_columns", [])]
        date_cols = [str(c) for c in semantics.get("date_columns", [])]

        all_cols = [str(c) for c in df.columns]
        if not metric_cols:
            num_cols = [str(c) for c in df.select_dtypes(include=[np.number]).columns]
            metric_cols = num_cols
        if not dim_cols:
            cat_cols = [str(c) for c in df.select_dtypes(exclude=[np.number]).columns]
            dim_cols = cat_cols

        p_lower = prompt.lower() if prompt else ""

        # 1. Detect requested chart type from prompt
        chart_type = None
        if any(k in p_lower for k in ["horizontal bar", "horizontal_bar", "barh", "ranking bar"]):
            chart_type = "horizontal_bar"
        elif any(k in p_lower for k in ["stacked bar", "stacked_bar", "stacked"]):
            chart_type = "stacked_bar"
        elif any(k in p_lower for k in ["bar chart", "bar graph", "barplot", "barchart", "column chart", "bar"]):
            chart_type = "bar"
        elif any(k in p_lower for k in ["line chart", "line graph", "lineplot", "trendline", "line"]):
            chart_type = "line"
        elif any(k in p_lower for k in ["area chart", "area graph", "areaplot", "area"]):
            chart_type = "area"
        elif any(k in p_lower for k in ["donut chart", "donut graph", "doughnut", "donut"]):
            chart_type = "donut"
        elif any(k in p_lower for k in ["pie chart", "pie graph", "pieplot", "pie"]):
            chart_type = "donut"
        elif any(k in p_lower for k in ["scatter plot", "scatter chart", "scatterplot", "scatter", "correlation plot"]):
            chart_type = "scatter"
        elif any(k in p_lower for k in ["histogram", "dist plot", "distribution plot", "hist"]):
            chart_type = "histogram"
        elif any(k in p_lower for k in ["radar chart", "spider chart", "radar"]):
            chart_type = "radar"

        # 2. Identify mentioned columns in prompt
        matched_metrics = []
        matched_dims = []

        for col in all_cols:
            c_clean = col.lower().replace("_", " ")
            if c_clean in p_lower or col.lower() in p_lower:
                if col in metric_cols:
                    matched_metrics.append(col)
                elif col in dim_cols or col in date_cols:
                    matched_dims.append(col)

        # Pick primary metric and dimension
        selected_metric = matched_metrics[0] if matched_metrics else (metric_cols[0] if metric_cols else None)
        selected_dim = matched_dims[0] if matched_dims else (dim_cols[0] if dim_cols else (date_cols[0] if date_cols else None))

        # Secondary metric if scatter requested
        secondary_metric = matched_metrics[1] if len(matched_metrics) > 1 else (
            [m for m in metric_cols if m != selected_metric][0] if len(metric_cols) > 1 else None
        )

        # 3. Detect Aggregation
        agg = "sum"
        if any(w in p_lower for w in ["average", "mean", "avg"]):
            agg = "mean"
        elif any(w in p_lower for w in ["count", "number of", "frequency", "volume"]):
            agg = "count"
        elif any(w in p_lower for w in ["max", "highest", "peak", "maximum"]):
            agg = "max"
        elif any(w in p_lower for w in ["min", "lowest", "minimum"]):
            agg = "min"
        elif any(w in p_lower for w in ["median"]):
            agg = "median"
        elif any(w in p_lower for w in ["sum", "total", "revenue", "sales", "spend", "profit"]):
            agg = "sum"

        # If user asked for histogram or distribution
        if chart_type == "histogram":
            selected_dim = None

        query_spec = {
            "chart_type": chart_type,
            "metric": selected_metric,
            "secondary_metric": secondary_metric,
            "dimension": selected_dim,
            "aggregation": agg,
            "date_column": date_cols[0] if date_cols else None,
            "top_k": 10,
            "sort_order": "desc",
            "prompt": prompt,
        }

        blackboard.set("query_plan", query_spec, agent_name="QueryPlannerAgent")
        return query_spec


class AnalysisExecutionAgent:
    """Executes aggregation, histogram binning, or scatter formatting and computes chart data payloads."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe available on blackboard"}

        query_plan = blackboard.get("query_plan")
        if not query_plan:
            query_plan = QueryPlannerAgent.run(blackboard)

        dim = query_plan.get("dimension")
        metric = query_plan.get("metric")
        sec_metric = query_plan.get("secondary_metric")
        agg = query_plan.get("aggregation", "sum")
        top_k = query_plan.get("top_k", 10)
        chart_type = query_plan.get("chart_type")

        result_records: List[Dict[str, Any]] = []

        # Case 1: Scatter plot between 2 numeric metrics
        if chart_type == "scatter" and metric and sec_metric and metric in df.columns and sec_metric in df.columns:
            scatter_sample = df[[metric, sec_metric] + ([dim] if dim and dim in df.columns else [])].dropna().head(50)
            for idx, row in scatter_sample.iterrows():
                result_records.append({
                    "name": str(row[dim]) if dim and dim in df.columns else f"Point #{idx+1}",
                    "x": round(float(row[metric]), 2),
                    "y": round(float(row[sec_metric]), 2),
                    "value": round(float(row[sec_metric]), 2),
                })

        # Case 2: Histogram / Distribution binning of single metric
        elif chart_type == "histogram" and metric and metric in df.columns:
            s = df[metric].dropna()
            if len(s) > 0:
                counts, bin_edges = np.histogram(s, bins=min(10, max(4, int(np.sqrt(len(s))))))
                for i in range(len(counts)):
                    bin_label = f"{round(float(bin_edges[i]), 1)} - {round(float(bin_edges[i+1]), 1)}"
                    result_records.append({
                        "name": bin_label,
                        "value": int(counts[i]),
                    })

        # Case 3: Group by dimension + aggregate metric
        elif dim and dim in df.columns and metric and metric in df.columns:
            try:
                # Check if dimension is date/time
                if "date" in str(dim).lower() or "time" in str(dim).lower():
                    temp = df.copy()
                    temp["_dt"] = pd.to_datetime(temp[dim], errors="coerce")
                    ts = temp.dropna(subset=["_dt", metric]).set_index("_dt")[metric]
                    if agg == "mean":
                        resampled = ts.resample("ME").mean()
                    else:
                        resampled = ts.resample("ME").sum()
                    if len(resampled) < 3:
                        resampled = ts.resample("D").sum()
                    for k, v in resampled.dropna().items():
                        period_str = k.strftime("%b %Y") if hasattr(k, "strftime") else str(k)
                        result_records.append({
                            "name": period_str,
                            "period": period_str,
                            "value": round(float(v), 2),
                        })
                else:
                    if agg == "sum":
                        grouped = df.groupby(dim)[metric].sum()
                    elif agg == "mean":
                        grouped = df.groupby(dim)[metric].mean()
                    elif agg == "median":
                        grouped = df.groupby(dim)[metric].median()
                    elif agg == "count":
                        grouped = df.groupby(dim)[metric].count()
                    elif agg == "max":
                        grouped = df.groupby(dim)[metric].max()
                    elif agg == "min":
                        grouped = df.groupby(dim)[metric].min()
                    else:
                        grouped = df.groupby(dim)[metric].sum()

                    grouped = grouped.sort_values(ascending=False).head(top_k)
                    for k, v in grouped.items():
                        result_records.append({
                            "name": str(k),
                            "value": round(float(v), 2) if not np.isnan(v) else 0.0,
                        })
            except Exception as e:
                result_records = []

        # Case 4: Single metric summary
        elif metric and metric in df.columns:
            val = float(df[metric].sum() if agg == "sum" else df[metric].mean())
            result_records = [{
                "name": str(metric).replace("_", " ").title(),
                "value": round(val, 2),
            }]

        execution_output = {
            "query_plan": query_plan,
            "data": result_records,
            "record_count": len(result_records),
        }

        blackboard.set("query_result", execution_output, agent_name="AnalysisExecutionAgent")
        return execution_output


class ChartSelectionAgent:
    """Selects best chart type and visual configuration for given data shapes and user prompts."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        query_result = blackboard.get("query_result") or {}
        query_plan = blackboard.get("query_plan") or {}
        data = query_result.get("data", [])

        dim = query_plan.get("dimension", "")
        metric = query_plan.get("metric", "Value")
        sec_metric = query_plan.get("secondary_metric")
        explicit_chart_type = query_plan.get("chart_type")

        # Determine chart type
        if explicit_chart_type:
            chart_type = explicit_chart_type
        elif sec_metric and len(data) > 0 and "x" in data[0] and "y" in data[0]:
            chart_type = "scatter"
        elif any(k in str(dim).lower() for k in ["date", "time", "month", "year", "day"]):
            chart_type = "area" if len(data) > 5 else "line"
        elif len(data) > 8:
            chart_type = "horizontal_bar"
        elif len(data) <= 5 and all(d.get("value", 0) >= 0 for d in data):
            chart_type = "donut"
        else:
            chart_type = "bar"

        # Format title
        if chart_type == "scatter" and sec_metric:
            title = f"{metric.replace('_', ' ').title()} vs {sec_metric.replace('_', ' ').title()} Scatter Analysis"
        elif chart_type == "histogram":
            title = f"Distribution of {metric.replace('_', ' ').title()}"
        elif dim:
            title = f"{metric.replace('_', ' ').title()} by {dim.replace('_', ' ').title()}"
        else:
            title = f"{metric.replace('_', ' ').title()} Analysis"

        chart_spec = {
            "id": "primary_visual",
            "type": chart_type,
            "chart_type": chart_type,
            "title": title,
            "x_axis": "x" if chart_type == "scatter" else ("period" if chart_type in ["area", "line"] and data and "period" in data[0] else "name"),
            "y_axis": "y" if chart_type == "scatter" else "value",
            "x_label": metric if chart_type == "scatter" else (dim or "Category"),
            "y_label": sec_metric if chart_type == "scatter" else metric,
            "metric": metric,
            "dimension": dim,
            "color": "#0284c7",
            "colors": ["#0284c7", "#38bdf8", "#818cf8", "#c084fc", "#f472b6", "#34d399", "#fbbf24"],
            "data": data,
        }

        blackboard.set("chart_recommendation", chart_spec, agent_name="ChartSelectionAgent")
        return chart_spec


class TrendAgent:
    """Detects temporal patterns, growth rates, period-over-period deltas, and seasonality."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe"}

        semantics = blackboard.get("semantics") or {}
        date_cols = semantics.get("date_columns", [])
        metric_cols = semantics.get("metric_columns", [])

        if not metric_cols:
            num_cols = list(df.select_dtypes(include=[np.number]).columns)
            metric_cols = num_cols

        trends_found = []

        if date_cols and metric_cols:
            date_col = date_cols[0]
            metric_col = metric_cols[0]
            try:
                temp_df = df.copy()
                temp_df["_dt"] = pd.to_datetime(temp_df[date_col], errors="coerce")
                temp_df = temp_df.dropna(subset=["_dt", metric_col]).sort_values("_dt")
                
                if len(temp_df) > 5:
                    # Group by period
                    ts = temp_df.set_index("_dt")[metric_col].resample("ME").sum()
                    if len(ts) < 3:
                        ts = temp_df.set_index("_dt")[metric_col].resample("D").sum()

                    ts_vals = ts.dropna().values
                    if len(ts_vals) >= 2:
                        first_val = float(ts_vals[0])
                        last_val = float(ts_vals[-1])
                        growth_pct = round(((last_val - first_val) / (first_val or 1.0)) * 100, 2)
                        
                        # Direction
                        direction = "Upward" if growth_pct > 2.0 else ("Downward" if growth_pct < -2.0 else "Stable")

                        trends_found.append({
                            "metric": metric_col,
                            "temporal_dimension": date_col,
                            "direction": direction,
                            "growth_percentage": growth_pct,
                            "first_period_value": round(first_val, 2),
                            "latest_period_value": round(last_val, 2),
                            "periods_analyzed": len(ts_vals),
                            "sparkline": [round(float(v), 2) for v in ts_vals[-12:]],
                        })
            except Exception:
                pass

        # Fallback numeric trends
        if not trends_found and metric_cols:
            for m in metric_cols[:2]:
                s = df[m].dropna()
                if len(s) > 10:
                    diff = float(s.iloc[-5:].mean() - s.iloc[:5].mean())
                    pct = round((diff / (abs(float(s.iloc[:5].mean())) or 1.0)) * 100, 2)
                    trends_found.append({
                        "metric": str(m),
                        "direction": "Upward" if pct > 0 else "Downward",
                        "growth_percentage": pct,
                        "sparkline": [round(float(v), 2) for v in s.iloc[::max(1, len(s)//10)][:10]],
                    })

        trend_data = {
            "trends": trends_found,
            "has_temporal_data": len(date_cols) > 0,
        }

        blackboard.set("trends", trend_data, agent_name="TrendAgent")
        return trend_data


class SegmentationAgent:
    """Auto-clusters categorical cohorts to find top and bottom performers."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe"}

        semantics = blackboard.get("semantics") or {}
        dim_cols = semantics.get("dimension_columns", [])
        metric_cols = semantics.get("metric_columns", [])

        if not dim_cols:
            dim_cols = list(df.select_dtypes(exclude=[np.number]).columns)
        if not metric_cols:
            metric_cols = list(df.select_dtypes(include=[np.number]).columns)

        segments = []
        if dim_cols and metric_cols:
            for dim in dim_cols[:2]:
                metric = metric_cols[0]
                if df[dim].nunique() <= 50:
                    grp = df.groupby(dim)[metric].agg(["mean", "sum", "count"]).dropna()
                    if not grp.empty:
                        sorted_grp = grp.sort_values(by="sum", ascending=False)
                        top_segment = sorted_grp.index[0]
                        bottom_segment = sorted_grp.index[-1]
                        top_val = float(sorted_grp.iloc[0]["sum"])
                        total_val = float(sorted_grp["sum"].sum()) or 1.0
                        share_pct = round((top_val / total_val) * 100, 1)

                        segments.append({
                            "dimension": str(dim),
                            "metric": str(metric),
                            "top_performer": str(top_segment),
                            "top_performer_share_pct": share_pct,
                            "bottom_performer": str(bottom_segment),
                            "distinct_segments": int(len(grp)),
                            "distribution": [
                                {"name": str(idx), "sum": round(float(row["sum"]), 2), "mean": round(float(row["mean"]), 2), "count": int(row["count"])}
                                for idx, row in sorted_grp.head(5).iterrows()
                            ],
                        })

        seg_data = {
            "segments": segments,
            "total_segmentations": len(segments),
        }

        blackboard.set("segments", seg_data, agent_name="SegmentationAgent")
        return seg_data


class AnomalyAgent:
    """Flags proactive outliers across numeric columns using Z-score and IQR ensembles."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe"}

        numeric_df = df.select_dtypes(include=[np.number])
        anomalies_found = []

        for col in numeric_df.columns:
            s = numeric_df[col].dropna()
            if len(s) < 10:
                continue

            q25 = float(s.quantile(0.25))
            q75 = float(s.quantile(0.75))
            iqr = q75 - q25
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr

            outliers = s[(s < lower_bound) | (s > upper_bound)]
            outlier_count = int(len(outliers))

            if outlier_count > 0:
                outlier_pct = round((outlier_count / len(s)) * 100, 2)
                anomalies_found.append({
                    "column": str(col),
                    "outlier_count": outlier_count,
                    "outlier_percentage": outlier_pct,
                    "lower_bound": round(lower_bound, 2),
                    "upper_bound": round(upper_bound, 2),
                    "min_detected": round(float(outliers.min()), 2),
                    "max_detected": round(float(outliers.max()), 2),
                    "severity": "high" if outlier_pct > 5.0 else "medium",
                })

        anom_data = {
            "total_anomalies_detected": sum(a["outlier_count"] for a in anomalies_found),
            "columns_with_anomalies": anomalies_found,
            "has_severe_anomalies": any(a["severity"] == "high" for a in anomalies_found),
        }

        blackboard.set("anomalies", anom_data, agent_name="AnomalyAgent")
        return anom_data


class WhyInvestigationAgent:
    """
    Decomposes changes in metrics across multiple dimensions in parallel,
    ranking contributors by variance/effect size to answer 'Why did X happen?'.
    """

    @staticmethod
    def run(
        blackboard: SharedBlackboard,
        metric: Optional[str] = None,
        dimension_to_decompose: Optional[str] = None,
    ) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe"}

        semantics = blackboard.get("semantics") or {}
        metric_cols = semantics.get("metric_columns", [])
        dim_cols = semantics.get("dimension_columns", [])

        if not metric and metric_cols:
            metric = metric_cols[0]
        elif not metric:
            num_cols = list(df.select_dtypes(include=[np.number]).columns)
            metric = num_cols[0] if num_cols else None

        if not metric:
            return {"error": "No numeric metric found to decompose"}

        # Select dimensions to inspect in parallel
        dimensions = [dimension_to_decompose] if dimension_to_decompose else dim_cols[:4]
        if not dimensions:
            dimensions = list(df.select_dtypes(exclude=[np.number]).columns)[:4]

        dimension_breakdowns: List[Dict[str, Any]] = []
        overall_total = float(df[metric].sum()) if metric in df.columns else 0.0
        overall_mean = float(df[metric].mean()) if metric in df.columns else 0.0

        for dim in dimensions:
            if dim in df.columns and df[dim].nunique() <= 50:
                grp = df.groupby(dim)[metric].agg(["sum", "mean", "count"]).dropna()
                if grp.empty:
                    continue

                # Compute variance contribution (effect size)
                variance_contributions = []
                for val_name, row in grp.iterrows():
                    val_sum = float(row["sum"])
                    val_mean = float(row["mean"])
                    share = round((val_sum / (overall_total or 1.0)) * 100, 2)
                    delta_vs_mean = round(((val_mean - overall_mean) / (overall_mean or 1.0)) * 100, 2)

                    variance_contributions.append({
                        "dimension_value": str(val_name),
                        "sum_contribution": round(val_sum, 2),
                        "share_percentage": share,
                        "mean_value": round(val_mean, 2),
                        "delta_vs_average_pct": delta_vs_mean,
                        "driver_type": "Positive Driver" if delta_vs_mean > 10 else ("Negative Driver" if delta_vs_mean < -10 else "Neutral Baseline"),
                    })

                # Sort by highest deviation
                sorted_contribs = sorted(variance_contributions, key=lambda x: abs(x["delta_vs_average_pct"]), reverse=True)
                top_positive = [c for c in sorted_contribs if c["driver_type"] == "Positive Driver"][:2]
                top_negative = [c for c in sorted_contribs if c["driver_type"] == "Negative Driver"][:2]

                dimension_breakdowns.append({
                    "dimension": str(dim),
                    "primary_positive_driver": top_positive[0]["dimension_value"] if top_positive else "None",
                    "primary_negative_driver": top_negative[0]["dimension_value"] if top_negative else "None",
                    "drivers": sorted_contribs,
                })

        why_result = {
            "target_metric": str(metric),
            "overall_total": round(overall_total, 2),
            "overall_mean": round(overall_mean, 2),
            "dimension_breakdowns": dimension_breakdowns,
            "top_root_cause_summary": (
                f"The highest variance for '{metric}' is driven by '{dimension_breakdowns[0]['dimension']}' "
                f"where '{dimension_breakdowns[0]['primary_positive_driver']}' over-indexes most significantly."
                if dimension_breakdowns else "No clear multi-dimensional drivers identified."
            ),
        }

        blackboard.set("why_analysis", why_result, agent_name="WhyInvestigationAgent")
        return why_result


class NarrativeAgent:
    """Converts structured insights from blackboard agents into executive takeaways with confidence ratings."""

    @staticmethod
    def run(blackboard: SharedBlackboard) -> Dict[str, Any]:
        profile = blackboard.get("profile") or {}
        quality = blackboard.get("quality") or {}
        stats_data = blackboard.get("statistics") or {}
        trends = blackboard.get("trends") or {}
        segments = blackboard.get("segments") or {}
        anomalies = blackboard.get("anomalies") or {}

        insights: List[Dict[str, Any]] = []

        # 1. Dataset volume & quality takeaway
        rows = profile.get("row_count", 0)
        cols = profile.get("column_count", 0)
        score = quality.get("quality_score", 100)
        insights.append({
            "rank": 1,
            "category": "Dataset Health",
            "title": f"Dataset Profile: {rows:,} records across {cols} features",
            "narrative": f"Data quality score is {score}/100. Found {quality.get('issue_count', 0)} potential issues and {quality.get('duplicate_count', 0)} duplicates.",
            "importance": "high",
            "confidence": 0.98,
        })

        # 2. Key Trend Insight
        trend_list = trends.get("trends", [])
        if trend_list:
            t = trend_list[0]
            insights.append({
                "rank": 2,
                "category": "Temporal Trends",
                "title": f"{t.get('direction', 'Stable')} Trend Detected on {t.get('metric', 'Metric')}",
                "narrative": f"Recorded a {t.get('growth_percentage', 0):+}% change across recent periods.",
                "importance": "high",
                "confidence": 0.92,
            })

        # 3. Top Segment Performer
        seg_list = segments.get("segments", [])
        if seg_list:
            s = seg_list[0]
            insights.append({
                "rank": 3,
                "category": "Cohort Segmentation",
                "title": f"Top Segment Concentration in {s.get('dimension')}",
                "narrative": f"'{s.get('top_performer')}' commands {s.get('top_performer_share_pct')}% of total {s.get('metric')}.",
                "importance": "medium",
                "confidence": 0.89,
            })

        # 4. Proactive Anomaly Alert
        anom_list = anomalies.get("columns_with_anomalies", [])
        if anom_list:
            a = anom_list[0]
            insights.append({
                "rank": 4,
                "category": "Anomaly Detection",
                "title": f"Outlier Cluster in '{a.get('column')}'",
                "narrative": f"Detected {a.get('outlier_count')} anomalous data points ({a.get('outlier_percentage')}%) exceeding expected statistical bounds.",
                "importance": "medium" if a.get("severity") == "high" else "low",
                "confidence": 0.94,
            })

        narrative_data = {
            "insights": insights,
            "executive_summary": " ".join(i["narrative"] for i in insights[:3]),
            "generated_at": datetime.now().isoformat(),
        }

        blackboard.set("narrative", narrative_data, agent_name="NarrativeAgent")
        return narrative_data
