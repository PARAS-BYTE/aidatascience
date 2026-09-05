from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


HIERARCHY_DEFINITIONS = {
    "geography": [
        ["region", "state", "city"],
        ["country", "region", "city"],
        ["country", "state", "city"],
        ["state", "city"],
    ],
    "time": [
        ["year", "quarter", "month", "day"],
        ["year", "month", "day"],
        ["year", "quarter"],
    ],
    "organization": [
        ["department", "team", "employee"],
        ["category", "subcategory", "product_name"],
        ["segment", "category", "sub_category"],
    ]
}



def detect_hierarchies(df: pd.DataFrame, dim_cols: List[str]) -> List[Dict[str, Any]]:
    cols_lower_map = {str(c).lower().replace(" ", "_"): str(c) for c in df.columns}
    detected = []

    for h_type, patterns in HIERARCHY_DEFINITIONS.items():
        for pattern in patterns:
            matched = [cols_lower_map[p] for p in pattern if p in cols_lower_map]
            if len(matched) >= 2:
                if not any(d["levels"] == matched for d in detected):
                    detected.append({
                        "name": f"{h_type.title()} Drill Hierarchy",
                        "type": h_type,
                        "levels": matched,
                        "current_level": 0,
                    })
                break

    if not detected and len(dim_cols) >= 2:
        detected.append({
            "name": "Dimension Drill Hierarchy",
            "type": "custom",
            "levels": [str(d) for d in dim_cols[:3]],
            "current_level": 0,
        })

    return detected


def suggest_filters(df: Optional[pd.DataFrame] = None, dataset_profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    filters = []

    if df is not None and not df.empty:
        for col in df.columns:
            series = df[col].dropna()
            if series.empty:
                continue

            col_str = str(col)
            col_lower = col_str.lower()
            is_date = (
                pd.api.types.is_datetime64_any_dtype(series)
                or any(k in col_lower for k in ["date", "time", "timestamp", "created_at", "year", "period"])
            )

            if is_date:
                try:
                    dt_series = pd.to_datetime(series, errors="coerce").dropna()
                    if not dt_series.empty:
                        filters.append({
                            "column": col_str,
                            "title": col_str.replace("_", " ").title(),
                            "control": "date_range",
                            "min": dt_series.min().strftime("%Y-+m-%d") if hasattr(dt_series.min(), "strftime") else str(dt_series.min()),
                            "max": dt_series.max().strftime("%Y-%m-%d") if hasattr(dt_series.max(), "strftime") else str(dt_series.max()),
                            "options": [],
                        })
                        continue
                except Exception:
                    pass

            if pd.api.types.is_numeric_dtype(series) and not col_lower.endswith("_id") and col_lower != "id":
                c_min = float(series.min())
                c_max = float(series.max())
                if c_min != c_max:
                    filters.append({
                        "column": col_str,
                        "title": col_str.replace("_", " ").title(),
                        "control": "range_slider",
                        "min": round(c_min, 2),
                        "max": round(c_max, 2),
                        "options": [],
                    })
            else:
                nunique = series.nunique()
                if 1 < nunique <= 60:
                    unique_vals = [str(x) for x in series.unique()[:30]]
                    filters.append({
                        "column": col_str,
                        "title": col_str.replace("_", " ").title(),
                        "control": "multiselect_dropdown",
                        "options": unique_vals,
                    })

    elif dataset_profile:
        for col in dataset_profile.get("columns", []):
            name = col.get("name", "")
            sem_type = col.get("semantic_type", "")
            c_type = col.get("type", "")
            card = col.get("cardinality", 999)

            if sem_type == "date" or c_type in ["date", "datetime"]:
                filters.append({
                    "column": name,
                    "title": name.replace("_", " ").title(),
                    "control": "date_range",
                    "options": [],
                })
            elif (c_type == "categorical" or sem_type == "categorical") and card <= 50:
                filters.append({
                    "column": name,
                    "title": name.replace("_", " ").title(),
                    "control": "multiselect_dropdown",
                    "options": [str(x) for x in col.get("unique_values", [])[:30]],
                })
            elif c_type in ["numeric", "int", "float", "integer", "number"] and sem_type != "id":
                filters.append({
                    "column": name,
                    "title": name.replace("_", " ").title(),
                    "control": "range_slider",
                    "min": float(col.get("min", 0)),
                    "max": float(col.get("max", 100)),
                    "options": [],
                })

    return filters[:6]
