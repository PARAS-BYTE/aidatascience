from typing import Dict, Any, Optional
import duckdb
import pandas as pd
from app.services.query_engine import build_where_clause


def _shift_date_range(current_filters: dict, date_col: Optional[str]) -> dict:
    "relative period shift for PRE-TOTAL comparison"
    prior = current_filters.copy()
    if date_col and date_col in prior:
        val = prior[date_col]
        if isinstance(val, dict) and "start" in val and "end" in val:
            try:
                s = pd.to_datetime(val["start"])
                e = pd.to_datetime(val["end"])
                diff = e - s
                prior_s = (s - diff).strftime("%Y-%m-%d")
                prior_e = s.strftime("%Y-%m-%d")
                prior[date_col] = {"start": prior_s, "end": prior_e}
            except Exception:
                pass
    return prior


def compute_kpi(con: duckdb.DuckDBPyConnection, metric: str, agg: str, current_filters: dict, date_col: Optional[str] = None) -> dict:
    """
    Compute KPI value plus delta percentage to prior comparable period.
    """
    agg_upper = str(agg).upper()
    agg_clean = "AVG" if agg_upper in ["MEAN", "AVG"] else ("COUNT" if agg_upper == "COUNT" else "SUM")
    agg_expr = "COUNT(*)" if metric == "row_count" or agg_clean == "COUNT" else f'{agg_clean}("{metric}")'


    where_curr, params_curr = build_where_clause(current_filters)
    sql_curr = f"SELECT {agg_expr} FROM dataset {where_curr}"
    row_curr = con.execute(sql_curr, params_curr).fetchone()
    current_val = float(row_curr[0]) if (row_curr and row_curr[0] is not None) else 0.0


    prior_filters = _shift_date_range(current_filters, date_col)
    where_prior, params_prior = build_where_clause(prior_filters)
    sql_prior = f"SELECT {agg_expr} FROM dataset {where_prior}"
    row_prior = con.execute(sql_prior, params_prior).fetchone()
    prior_val = float(row_prior[0]) if (row_prior and row_prior[0] is not None) else None

    delta_pct = 0.0
    if prior_val is not None and prior_val != 0.0:
        delta_raw = (current_val - prior_val) / abs(prior_val)
        delta_pct = round(delta_raw * 100, 1)

    trend = "up" if delta_pct > 0 else ("down" if delta_pct < 0 else "neutral")
    return {
        "value": round(current_val, 2),
        "prior_value": round(prior_val, 2) if prior_val is not None else None,
        "delta_percentage": delta_pct,
        "trend_direction": trend,
        "is_positive": delta_pct >= 0,
    }
