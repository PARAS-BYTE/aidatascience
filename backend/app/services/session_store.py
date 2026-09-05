from typing import Dict, Any, Optional
import duckdb
import pandas as pd
from sqlalchemy.orm import Session
from app.services.multi_agent.blackboard import get_blackboard
from app.services.dataset_service import DatasetService

# Cache of DuckDB connections keyed by dashboard_id / session_id / dataset_id
_DUCKDB_CONNECTIONS: Dict[str, duckdb.DuckDBPyConnection] = {}
_CHART_SPECS_CACHE: Dict[str, Dict[str, Any]] = {}


def register_dataset_in_duckdb(df_input: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    """Create in-memory DuckDB session registering the active dataframe."""
    con = duckdb.connect(":memory:")
    df_clean = df_input.copy()
    # Ensure column names are strings
    df_clean.columns = [str(c) for c in df_clean.columns]
    con.register("dataset_df", df_clean)
    con.execute("CREATE OR REPLACE TABLE dataset AS SELECT * FROM dataset_df")
    return con


def get_duckdb_connection(
    identifier: str,
    dataset_id: Optional[str] = None,
    db: Optional[Session] = None,
    df_override: Optional[pd.DataFrame] = None,
) -> duckdb.DuckDBPyConnection:
    """
    Retrieve an existing DuckDB connection for a session/dashboard,
    or initialize one from Blackboard / database without re-reading from disk every turn.
    """
    cache_key = str(identifier)
    if cache_key in _DUCKDB_CONNECTIONS:
        return _DUCKDB_CONNECTIONS[cache_key]

    df = df_override
    if df is None:
        # 1. Try to get from SharedBlackboard
        blackboard = get_blackboard(session_id=identifier, dataset_id=dataset_id)
        df = blackboard.get_df()

    if df is None and dataset_id and db is not None:
        # 2. Load from DatasetService
        try:
            df = DatasetService.get_dataframe(db=db, dataset_id=dataset_id)
        except Exception:
            pass

    if df is None:
        # 3. Create mock dataset for safety if nothing loaded
        df = pd.DataFrame({
            "region": ["North", "South", "East", "West"],
            "state": ["NY", "TH", "MA", "CA"],
            "city": ["NYC", "Austin", "Boston", "LA"],
            "sales": [15000, 22000, 18000, 31000],
            "profit": [3500, 5400, 4100, 8200],
            "date": ["2024-01-15", "2024-02-15", "2024-03-15", "2024-04-15"],
        })

    con = register_dataset_in_duckdb(df)
    _DUCKDB_CONNECTIONS[cache_key] = con
    if dataset_id:
        _DUCKDB_CONNECTIONS[str(dataset_id)] = con
    return con


def get_chart_spec(identifier: str, chart_id: str, dataset_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Locate chart spec from blackboard or local registry.
    """
    cache_key = f"{identifier}:{chart_id}"
    if cache_key in _CHART_SPECS_CACHE:
        return _CHART_SPECS_CACHE[cache_key]

    blackboard = get_blackboard(session_id=identifier, dataset_id=dataset_id)
    dashboard_spec = blackboard.get("dashboard_spec") or {}

    all_charts = []
    if dashboard_spec.get("primary_chart"):
        all_charts.append(dashboard_spec["primary_chart"])
    all_charts.extend(dashboard_spec.get("secondary_charts", []))
    all_charts.extend(dashboard_spec.get("charts", []))

    for c in all_charts:
        if c.get("id") == chart_id:
            _CHART_SPECS_CACHE[cache_key] = c
            return c

    # Default fallback chart spec if not registered
    return {
        "id": chart_id,
        "type": "bar",
        "metric": "sales",
        "aggregation": "SUM",
        "dimension": "region",
        "listens_to_filters": [],
        "emits_filter_on_click": "region",
    }

