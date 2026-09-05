from typing import Tuple, List, Any, Dict, Optional
import duckdb

valid_aggs = {"SUM": "SUM", "AVG": "AVG", "MEAN": "AVG", "COUNT": "COUNT", "MIN": "MIN", "MAX": "MAX"}


def build_where_clause(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Construct deterministic, secure WHERE clause and parameters from filter map."""
    where_clauses, params = [], []
    for col, value in filters.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, (list, tuple)):
            if not value:
                continue
            placeholders = ",".join(["?"] * len(value))
            where_clauses.append(f'"{col}" IN ({placeholders})')
            params.extend([str(v) if not isinstance(v, (int, float)) else v for v in value])
        elif isinstance(value, dict):
            if "start" in value and "end" in value:
                where_clauses.append(f'"{col}" BETWEEN ? AND ?')
                params.extend([str(value["start"]), str(value["end"])])
            elif "min" in value or "max" in value:
                if "min" in value and value["min"] is not None:
                    where_clauses.append(f'"{col}" >= ?')
                    params.append(float(value["min"]))
                if "max" in value and value["max"] is not None:
                    where_clauses.append(f'"{col}" <= ?')
                    params.append(float(value["max"]))
        else:
            where_clauses.append(f'"{col}" = ?')
            params.append(value)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return where_sql, params


def build_chart_query(chart: Dict[str, Any], filters: Dict[str, Any], override_dim: Optional[str] = None) -> Tuple[str, List[Any]]:
    """
    Parameterized, SQL-injection-safe chart aggregation query builder for DuckDB.
    """
    metric = chart.get("metric") or "value"
    agg = valid_aggs.get(str(chart.get("aggregation", "SUM")).upper(), "SUM")
    dim = override_dim or chart.get("dimension") or "category"

    where_sql, params = build_where_clause(filters)

    limit = chart.get("limit") or 30
    limit_sql = f"LIMIT {limit}" if limit else ""
    sort_dir = "asc" if str(chart.get("sort", "desc")).lower() == "asc" else "desc"
    order_sql = f"ORDER BY value {sort_dir}"

    if metric == "row_count" or agg == "COUNT":
        agg_expr = "COUNT(*)"
    else:
        agg_expr = f'{agg}("{metric}")'

    sql = f'''
        SELECT "{dim}" AS name, "{dim}" AS category, {agg_expr} AS value
        FROM dataset
        {where_sql}
        GROUP BY "{dim}"
        {order_sql}
        {limit_sql}
    '''
    return sql, params


def run_chart_query(con: duckdb.DuckDBPyConnection, chart: Dict[str, Any], filters: Dict[str, Any], override_dim: Optional[str] = None):
    """Execute a chart query against DuckDB and return pandas DataFrame."""
    sql, params = build_chart_query(chart, filters, override_dim=override_dim)
    return con.execute(sql, params).fetchdf()

