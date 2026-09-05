from typing import Dict, Any, Optional, List
import numpy as np
from fastapi import APIRouter, HTTPException, Depends, Body, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.dashboard import ChartSpec, FilterSpec, DashboardSpec, DashboardPatch, ChartQueryRequest
from app.services.query_engine import run_chart_query
from app.services.session_store import get_duckdb_connection, get_chart_spec
from app.services.kpi_service import compute_kpi
from app.services.multi_agent.blackboard import get_blackboard, sanitize_for_json

router = APIRouter(prefix="/dashboard", tags=["Interactive Power BI Dashboard"])


@router.post("/{dashboard_id}/query-chart")
async def query_chart(
    dashboard_id: str,
    payload: ChartQueryRequest,
    dataset_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Execute a fast, parameterized, session-cached DuckDB query for a specific chart
    given the active cross-filters and optional drill-down dimension.
    """
    chart_id = payload.chart_id
    filters = payload.filters or {}
    dimension = payload.dimension

    chart = get_chart_spec(dashboard_id, chart_id, dataset_id=dataset_id)
    if not chart:
        raise HTTPException(status_code=404, detail="chart not found")

    try:
        con = get_duckdb_connection(dashboard_id, dataset_id=dataset_id, db=db)
        df = run_chart_query(con, chart, filters, override_dim=dimension)
        # Convert nan/inf to normalized JSON
        records = df.to_dict(orient="records") if hasattr(df, "to_dict") else []
        return {
            "chart_id": chart_id,
            "data": sanitize_for_json(records),
            "dimension": dimension or chart.get("dimension"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dashboard_id}/query-kpis")
async def query_kpis(
    dashboard_id: str,
    payload: Dict[str, Any] = Body(...),
    dataset_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Compute updated KPIs with trend deltas against prior period for all active kpi cards.
    """
    filters = payload.get("filters", {})
    date_col = payload.get("date_col")

    blackboard = get_blackboard(session_id=dashboard_id, dataset_id=dataset_id)
    dashboard_spec = blackboard.get("dashboard_spec") or {}
    kpi_cards = dashboard_spec.get("kpi_cards", [])

    if not kpi_cards:
        return {"kpis": []}

    con = get_duckdb_connection(dashboard_id, dataset_id=dataset_id, db=db)
    results = []

    for kpi in kpi_cards:
        metric = kpi.get("metric_key", "value")
        agg = kpi.get("aggregation", "sum")
        res = compute_kpi(con, metric, agg, filters, date_col=date_col)
        if_financial = any(k in str(metric).lower() for k in ["sales", "revenue", "price", "profit", "spend"])
        fmt_str = f"${res['value']:,.0f}" if (if_financial and res["value"] > 1000) else (f"${res['value']:,.2f}" if if_financial else f"{res['value']:,.2f}")
        results.append({
            "id": kpi.get("id", f"kpi_{metric}"),
            "metric_key": metric,
            "title": kpi.get("title", metric),
            "value": res["value"],
            "formatted_value": fmt_str,
            "delta_percentage": res["delta_percentage"],
            "trend_direction": res["trend_direction"],
            "is_positive": res["is_positive"],
            "sparkline": kpi.get("sparkline", []),
            "subtitle": kpi.get("subtitle") or "Filtered Value",
        })

    return {"kpis": results}


@router.post("/{dashboard_id}/patch")
async def apply_patch(
    dashboard_id: str,
    patch: DashboardPatch,
    dataset_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Apply a discrete DashboardPatch modification to the dashboard spec.
    """
    blackboard = get_blackboard(session_id=dashboard_id, dataset_id=dataset_id)
    spec = blackboard.get("dashboard_spec") or {}

    if patch.op == "update_chart" and patch.chart_id and patch.changes:
        if spec.get("primary_chart") and spec["primary_chart"].get("id") == patch.chart_id:
            spec["primary_chart"].update(patch.changes)
        else:
            for c in spec.get("secondary_charts", []):
                if c.get("id") == patch.chart_id:
                    c.update(patch.changes)
                    break

    elif patch.op == "add_chart" and patch.chart:
        if "secondary_charts" not in spec:
            spec["secondary_charts"] = []
        spec["secondary_charts"].append(patch.chart.model_dump() if hasattr(patch.chart, "model_dump") else patch.chart.dict())

    elif patch.op == "remove_chart" and patch.chart_id:
        spec["secondary_charts"] = [c for c in spec.get("secondary_charts", []) if c.get("id") != patch.chart_id]

    elif patch.op == "add_filter" and patch.filter:
        if "filters" not in spec:
            spec["filters"] = []
        spec["filters"].append(patch.filter.model_dump() if hasattr(patch.filter, "model_dump") else patch.filter.dict())

    blackboard.set("dashboard_spec", spec, agent_name="DashboardPatchApplier")
    return {
        "status": "success",
        "patch": patch.model_dump() if hasattr(patch, "model_dump") else patch.dict(),
        "dashboard_spec": sanitize_for_json(spec),
    }

