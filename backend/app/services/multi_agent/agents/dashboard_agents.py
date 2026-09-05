"""
Dashboard Agents — The Power BI Layer for Self-Assembling Interactive Reports.
1. DashboardLayoutAgent: Formulates layout hierarchy (KPI cards with sparklines, primary trend, secondary breakdowns, slicers, drill-downs).
2. DashboardUpdateAgent: Dynamically patches and updates the existing dashboard spec on follow-up prompts.
"""
import copy
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.multi_agent.blackboard import SharedBlackboard


class DashboardLayoutAgent:
    """
    Builds a complete, Power BI-compatible interactive report specification
    from data stored in the shared blackboard.
    """

    @staticmethod
    def run(blackboard: SharedBlackboard, title: Optional[str] = None) -> Dict[str, Any]:
        df = blackboard.get_df()
        if df is None or df.empty:
            return {"error": "No dataframe on blackboard"}

        semantics = blackboard.get("semantics") or {}
        profile = blackboard.get("profile") or {}
        trends = blackboard.get("trends") or {}
        segments = blackboard.get("segments") or {}
        anomalies = blackboard.get("anomalies") or {}
        stats_data = blackboard.get("statistics") or {}
        narrative = blackboard.get("narrative") or {}

        metric_cols = semantics.get("metric_columns", [])
        dim_cols = semantics.get("dimension_columns", [])
        date_cols = semantics.get("date_columns", [])

        if not metric_cols:
            metric_cols = list(df.select_dtypes(include=[np.number]).columns)
        if not dim_cols:
            dim_cols = list(df.select_dtypes(exclude=[np.number]).columns)

        # 1. KPI Cards (Top visual row)
        kpi_cards: List[Dict[str, Any]] = []
        for idx, m in enumerate(metric_cols[:4]):
            series = df[m].dropna()
            total_val = float(series.sum())
            avg_val = float(series.mean())
            
            # Formulate sparkline
            if len(series) > 10:
                step = max(1, len(series) // 10)
                sparkline = [round(float(v), 2) for v in series.iloc[::step][:10]]
            else:
                sparkline = [round(float(v), 2) for v in series.tolist()]

            # Fake delta for demonstration based on first half vs second half
            mid = len(series) // 2
            first_half = series.iloc[:mid].mean() if mid > 0 else avg_val
            second_half = series.iloc[mid:].mean() if mid > 0 else avg_val
            delta = round(((second_half - first_half) / (abs(first_half) or 1.0)) * 100, 1)

            is_financial = any(k in str(m).lower() for k in ["sales", "revenue", "price", "profit", "amount", "spend", "cost", "salary"])
            
            kpi_cards.append({
                "id": f"kpi_{m}",
                "metric_key": str(m),
                "title": str(m).replace("_", " ").title(),
                "value": round(total_val if is_financial else avg_val, 2),
                "formatted_value": f"${total_val:,.0f}" if (is_financial and total_val > 1000) else (f"{avg_val:,.2f}" if not is_financial else f"${total_val:,.2f}"),
                "aggregation": "sum" if is_financial else "mean",
                "delta_percentage": delta,
                "trend_direction": "up" if delta > 0 else ("down" if delta < 0 else "neutral"),
                "is_positive": delta >= 0,
                "sparkline": sparkline,
                "subtitle": "Total Volume" if is_financial else "Dataset Average",
            })

        # Add records count KPI card if we have space
        if len(kpi_cards) < 4:
            kpi_cards.append({
                "id": "kpi_row_count",
                "metric_key": "row_count",
                "title": "Total Records",
                "value": len(df),
                "formatted_value": f"{len(df):,}",
                "aggregation": "count",
                "delta_percentage": 0.0,
                "trend_direction": "neutral",
                "is_positive": True,
                "sparkline": [len(df)] * 6,
                "subtitle": "Active Data Rows",
            })

        # 2. Primary Chart (Center stage — use explicit ChartSelectionAgent output if present)
        chart_rec = blackboard.get("chart_recommendation")
        primary_chart = None

        if chart_rec and isinstance(chart_rec, dict) and chart_rec.get("data"):
            primary_chart = {
                "id": "chart_primary_dynamic",
                "type": chart_rec.get("chart_type") or chart_rec.get("type", "bar"),
                "title": chart_rec.get("title") or "Custom Visual Overview",
                "x_axis": chart_rec.get("x_axis", "name"),
                "y_axis": chart_rec.get("y_axis", "value"),
                "x_label": chart_rec.get("x_label"),
                "y_label": chart_rec.get("y_label"),
                "metric": chart_rec.get("metric"),
                "dimension": chart_rec.get("dimension"),
                "data": chart_rec.get("data", []),
                "color": chart_rec.get("color", "#0284c7"),
                "colors": chart_rec.get("colors", ["#0284c7", "#38bdf8", "#818cf8", "#c084fc", "#f472b6"]),
            }

        # Fallback to temporal trend or first dimension if no custom recommendation
        if not primary_chart and date_cols and metric_cols:
            date_col = date_cols[0]
            metric_col = metric_cols[0]
            try:
                temp_df = df.copy()
                temp_df["_dt"] = pd.to_datetime(temp_df[date_col], errors="coerce")
                grouped = temp_df.dropna(subset=["_dt", metric_col]).set_index("_dt")[metric_col].resample("ME").sum()
                if len(grouped) < 3:
                    grouped = temp_df.dropna(subset=["_dt", metric_col]).set_index("_dt")[metric_col].resample("D").sum()
                
                chart_data = [
                    {"period": idx.strftime("%b %Y") if hasattr(idx, "strftime") else str(idx), "name": idx.strftime("%b %Y") if hasattr(idx, "strftime") else str(idx), "value": round(float(v), 2)}
                    for idx, v in grouped.items()
                ]
                primary_chart = {
                    "id": "chart_primary_trend",
                    "type": "area",
                    "title": f"{metric_col.replace('_', ' ').title()} Over Time",
                    "x_axis": "period",
                    "y_axis": "value",
                    "metric": metric_col,
                    "dimension": date_col,
                    "data": chart_data[:24],
                    "color": "#0284c7",
                }
            except Exception:
                pass

        if not primary_chart and dim_cols and metric_cols:
            dim_col = dim_cols[0]
            metric_col = metric_cols[0]
            grouped = df.groupby(dim_col)[metric_col].sum().sort_values(ascending=False).head(10)
            primary_chart = {
                "id": "chart_primary_bar",
                "type": "bar",
                "title": f"{metric_col.replace('_', ' ').title()} by {dim_col.replace('_', ' ').title()}",
                "x_axis": "name",
                "y_axis": "value",
                "metric": metric_col,
                "dimension": dim_col,
                "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in grouped.items()],
                "color": "#38bdf8",
            }

        # 3. Secondary Charts (Breakdowns, Treemaps, Donut charts)
        secondary_charts: List[Dict[str, Any]] = []

        # Secondary 1: Donut or Top 5 breakdown
        if len(dim_cols) > 0 and metric_cols:
            dim = dim_cols[min(1, len(dim_cols)-1)]
            metric = metric_cols[0]
            grp = df.groupby(dim)[metric].sum().sort_values(ascending=False).head(5)
            secondary_charts.append({
                "id": "chart_secondary_donut",
                "type": "donut",
                "title": f"Share by {dim.replace('_', ' ').title()}",
                "x_axis": "name",
                "y_axis": "value",
                "metric": metric,
                "dimension": dim,
                "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in grp.items()],
                "colors": ["#0284c7", "#38bdf8", "#818cf8", "#c084fc", "#f472b6"],
            })

        # Secondary 2: Horizontal Bar (Ranking)
        if len(dim_cols) > 1 and metric_cols:
            dim = dim_cols[min(2, len(dim_cols)-1)]
            metric = metric_cols[min(1, len(metric_cols)-1)]
            grp = df.groupby(dim)[metric].mean().sort_values(ascending=False).head(8)
            secondary_charts.append({
                "id": "chart_secondary_hbar",
                "type": "horizontal_bar",
                "title": f"Avg {metric.replace('_', ' ').title()} by {dim.replace('_', ' ').title()}",
                "x_axis": "value",
                "y_axis": "name",
                "metric": metric,
                "dimension": dim,
                "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in grp.items()],
                "color": "#818cf8",
            })

        # Secondary 3: Multi-metric correlation scatter if multiple metrics exist
        if len(metric_cols) >= 2:
            m1, m2 = metric_cols[0], metric_cols[1]
            sample_scatter = df[[m1, m2]].dropna().head(40)
            secondary_charts.append({
                "id": "chart_secondary_scatter",
                "type": "scatter",
                "title": f"{m1.replace('_', ' ').title()} vs {m2.replace('_', ' ').title()}",
                "x_axis": "x",
                "y_axis": "y",
                "x_label": m1,
                "y_label": m2,
                "data": [{"name": f"Item #{idx+1}", "x": round(float(r[m1]), 2), "y": round(float(r[m2]), 2)} for idx, r in sample_scatter.reset_index().iterrows()],
                "color": "#34d399",
            })

        from app.services.filter_suggester import suggest_filters, detect_hierarchies
        from app.services.session_store import register_dataset_in_duckdb, _DUCKDB_CONNECTIONS

        # 4. Intelligent Filters & Slicers
        filters_spec = suggest_filters(df)
        all_filter_cols = [f["column"] for f in filters_spec]

        # 5. Hierarchy Drill-Downs Detection
        drill_downs = detect_hierarchies(df, dim_cols)

        def configure_chart_contract(c: Dict[str, Any]) -> Dict[str, Any]:
            dim = c.get("dimension") or "category"
            c["emits_filter_on_click"] = str(dim)
            # Listens to all filter columns except its own dimension
            c["listens_to_filters"] = [col for col in all_filter_cols if col != dim]
            if not c["listens_to_filters"] and all_filter_cols:
                c["listens_to_filters"] = list(all_filter_cols)
            
            # Check for drillable hierarchy match
            c["drillable"] = False
            c["drill_path"] = None
            for h in drill_downs:
                if h.get("levels") and str(h["levels"][0]).lower() == str(dim).lower():
                    c["drillable"] = True
                    c["drill_path"] = h["levels"]
                    break
            
            if "aggregation" not in c:
                c["aggregation"] = "SUM"
            return c

        if primary_chart:
            primary_chart = configure_chart_contract(primary_chart)

        secondary_charts = [configure_chart_contract(c) for c in secondary_charts]
        all_charts_list = ([primary_chart] if primary_chart else []) + secondary_charts

        # Pre-cache duckdb connection for rapid queries
        try:
            con = register_dataset_in_duckdb(df)
            _DUCKDB_CONNECTIONS[str(blackboard.session_id)] = con
            if blackboard.dataset_id:
                _DUCKDB_CONNECTIONS[str(blackboard.dataset_id)] = con
        except Exception:
            pass

        dashboard_spec = {
            "id": f"dash_{blackboard.session_id}",
            "layout": "executive_bi",
            "title": title or "Executive Intelligence Dashboard",
            "subtitle": f"Self-assembling Power BI report • Generated from {len(df):,} records",
            "generated_at": datetime.now().isoformat(),
            "kpi_cards": kpi_cards,
            "primary_chart": primary_chart,
            "secondary_charts": secondary_charts,
            "charts": all_charts_list,
            "filters": filters_spec,
            "drill_downs": drill_downs,
            "cross_filtering_enabled": True,
            "insights_panel": True,
            "anomaly_badge_enabled": True,
            "insights": narrative.get("insights", []),
            "anomalies_summary": anomalies.get("columns_with_anomalies", [])[:3],
        }

        blackboard.set("dashboard_spec", dashboard_spec, agent_name="DashboardLayoutAgent")
        return dashboard_spec


class DashboardUpdateAgent:
    """
    Applies targeted updates, re-queries, and patches to the active dashboard spec
    based on natural-language user feedback.
    """

    @staticmethod
    def run(blackboard: SharedBlackboard, prompt: str) -> Dict[str, Any]:
        existing_spec = blackboard.get("dashboard_spec")
        df = blackboard.get_df()

        if not existing_spec:
            return DashboardLayoutAgent.run(blackboard)

        spec = copy.deepcopy(existing_spec)
        p_lower = prompt.lower()
        applied_patches = []

        # Check if prompt asks for a completely new chart with columns
        from app.services.multi_agent.agents.analysis_agents import QueryPlannerAgent, AnalysisExecutionAgent, ChartSelectionAgent
        
        # If user mentions specific columns or chart type in prompt, re-run query planner
        if any(c.lower() in p_lower for c in (df.columns if df is not None else [])) or any(k in p_lower for k in ["scatter", "histogram", "donut", "pie", "bar", "line", "area"]):
            QueryPlannerAgent.run(blackboard, prompt=prompt)
            AnalysisExecutionAgent.run(blackboard)
            chart_rec = ChartSelectionAgent.run(blackboard)
            if chart_rec and chart_rec.get("data"):
                spec["primary_chart"] = {
                    "id": "chart_primary_dynamic",
                    "type": chart_rec.get("chart_type", "bar"),
                    "title": chart_rec.get("title", "Updated Visual"),
                    "x_axis": chart_rec.get("x_axis", "name"),
                    "y_axis": chart_rec.get("y_axis", "value"),
                    "x_label": chart_rec.get("x_label"),
                    "y_label": chart_rec.get("y_label"),
                    "metric": chart_rec.get("metric"),
                    "dimension": chart_rec.get("dimension"),
                    "data": chart_rec.get("data", []),
                    "color": chart_rec.get("color", "#0284c7"),
                    "colors": chart_rec.get("colors", ["#0284c7", "#38bdf8", "#818cf8"]),
                }
                applied_patches.append(f"Updated primary chart to '{chart_rec.get('title')}' ({chart_rec.get('chart_type')})")

        # Fallback chart type toggles if columns not re-specified
        elif "stacked bar" in p_lower or "stacked" in p_lower:
            if "primary_chart" in spec and spec["primary_chart"]:
                spec["primary_chart"]["type"] = "stacked_bar"
                applied_patches.append("Changed primary chart to Stacked Bar")
        elif "horizontal bar" in p_lower or "horizontal" in p_lower:
            if "primary_chart" in spec and spec["primary_chart"]:
                spec["primary_chart"]["type"] = "horizontal_bar"
                applied_patches.append("Changed primary chart to Horizontal Bar")
        elif "line" in p_lower:
            if "primary_chart" in spec and spec["primary_chart"]:
                spec["primary_chart"]["type"] = "line"
                applied_patches.append("Changed primary chart to Line Chart")
        elif "bar" in p_lower:
            if "primary_chart" in spec and spec["primary_chart"]:
                spec["primary_chart"]["type"] = "bar"
                applied_patches.append("Changed primary chart to Bar Chart")
        elif "area" in p_lower:
            if "primary_chart" in spec and spec["primary_chart"]:
                spec["primary_chart"]["type"] = "area"
                applied_patches.append("Changed primary chart to Area Chart")
        elif "donut" in p_lower or "pie" in p_lower:
            if "primary_chart" in spec and spec["primary_chart"]:
                spec["primary_chart"]["type"] = "donut"
                applied_patches.append("Changed primary chart to Donut Chart")

        # 2. Add or modify filters
        if df is not None:
            for col in df.columns:
                if f"filter for {str(col).lower()}" in p_lower or f"add filter {str(col).lower()}" in p_lower or f"filter by {str(col).lower()}" in p_lower:
                    unique_vals = [str(x) for x in df[col].dropna().unique()[:15]]
                    existing_filter = next((f for f in spec.get("filters", []) if f["column"] == str(col)), None)
                    if not existing_filter:
                        spec["filters"].append({
                            "column": str(col),
                            "title": str(col).replace("_", " ").title(),
                            "type": "categorical_select",
                            "options": unique_vals,
                            "selected": [],
                        })
                        applied_patches.append(f"Added global filter slicer for '{col}'")

        # 3. Filter to a specific value mentioned in prompt
        if df is not None:
            for col in df.columns:
                for val in df[col].dropna().unique()[:20]:
                    if str(val).lower() in p_lower and len(str(val)) > 2:
                        for f in spec.get("filters", []):
                            if f["column"] == str(col) and str(val) not in f["selected"]:
                                f["selected"].append(str(val))
                                applied_patches.append(f"Applied filter: {col} = '{val}'")

        spec["last_modified_prompt"] = prompt
        spec["applied_patches"] = applied_patches or ["Refreshed dashboard components with latest parameters"]
        spec["updated_at"] = datetime.now().isoformat()

        blackboard.set("dashboard_spec", spec, agent_name="DashboardUpdateAgent")
        return spec
