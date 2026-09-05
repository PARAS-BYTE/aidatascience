"""
Text-to-SQL Service ("Ask Your Data") — Translates natural language questions into safe SQL,
executes them against DuckDB, and recommends interactive visualization chart types.
"""
import re
import json
import logging
from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Dataset
from app.services.profiler import DatasetProfiler
from app.core.config import settings

logger = logging.getLogger(__name__)

FORBIDDEN_SQL = ["drop ", "delete ", "insert ", "update ", "alter ", "truncate ", "create ", "replace ", "attach ", "copy "]


class Text2SQLService:
    @staticmethod
    def _display_value(value: Any) -> str:
        """Format a computed scalar for a human answer without inventing facts."""
        if isinstance(value, float):
            return f"{value:,.4f}".rstrip("0").rstrip(".")
        return str(value)

    @staticmethod
    def validate_sql(sql: str) -> bool:
        """Ensure SQL query is strictly a read-only SELECT statement."""
        cleaned = sql.strip().lower()
        if not (cleaned.startswith("select") or cleaned.startswith("with")):
            return False
        for forbidden in FORBIDDEN_SQL:
            if forbidden in cleaned:
                return False
        return True

    @classmethod
    def generate_sql(cls, question: str, df: pd.DataFrame) -> str:
        """
        Generate safe DuckDB SQL query from question text.
        Combines intelligent pattern matching with schema matching.
        """
        q = question.lower()
        cols = df.columns.tolist()
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
        date_cols = [c for c in cols if any(k in c.lower() for k in ["date", "time", "year", "month", "day"])]

        # Find mentioned columns in prompt
        mentioned_num = [c for c in num_cols if c.lower() in q]
        mentioned_cat = [c for c in cat_cols if c.lower() in q]
        mentioned_date = [c for c in date_cols if c.lower() in q]

        # Top N query
        top_match = re.search(r"top\s+(\d+)", q)
        limit = int(top_match.group(1)) if top_match else 10

        # Pattern 1: Count / How many
        if any(w in q for w in ["how many", "total count", "number of rows", "total records"]):
            if mentioned_cat:
                cat = mentioned_cat[0]
                return f'SELECT "{cat}", COUNT(*) as count FROM df GROUP BY "{cat}" ORDER BY count DESC LIMIT {limit}'
            return 'SELECT COUNT(*) as total_rows FROM df'

        # Pattern 2: Average / Mean by category
        if any(w in q for w in ["average", "avg", "mean"]) and mentioned_num:
            num = mentioned_num[0]
            if mentioned_cat:
                cat = mentioned_cat[0]
                return f'SELECT "{cat}", ROUND(AVG("{num}"), 2) as avg_{num} FROM df GROUP BY "{cat}" ORDER BY avg_{num} DESC LIMIT {limit}'
            elif mentioned_date:
                dt = mentioned_date[0]
                return f'SELECT "{dt}", ROUND(AVG("{num}"), 2) as avg_{num} FROM df GROUP BY "{dt}" ORDER BY "{dt}" ASC LIMIT 30'
            return f'SELECT ROUND(AVG("{num}"), 2) as avg_{num} FROM df'

        # Pattern 3: Sum / Total by category
        if any(w in q for w in ["total", "sum"]) and mentioned_num:
            num = mentioned_num[0]
            if mentioned_cat:
                cat = mentioned_cat[0]
                return f'SELECT "{cat}", ROUND(SUM("{num}"), 2) as total_{num} FROM df GROUP BY "{cat}" ORDER BY total_{num} DESC LIMIT {limit}'
            return f'SELECT ROUND(SUM("{num}"), 2) as total_{num} FROM df'

        # Pattern 4: Top records / Highest / Lowest
        if any(w in q for w in ["highest", "top", "max", "best"]) and (mentioned_num or num_cols):
            num = mentioned_num[0] if mentioned_num else num_cols[0]
            display_cols = (mentioned_cat[:2] or cat_cols[:2]) + [num]
            col_sql = ", ".join([f'"{c}"' for c in set(display_cols)])
            return f'SELECT {col_sql} FROM df ORDER BY "{num}" DESC LIMIT {limit}'

        if any(w in q for w in ["lowest", "bottom", "min", "worst"]) and (mentioned_num or num_cols):
            num = mentioned_num[0] if mentioned_num else num_cols[0]
            display_cols = (mentioned_cat[:2] or cat_cols[:2]) + [num]
            col_sql = ", ".join([f'"{c}"' for c in set(display_cols)])
            return f'SELECT {col_sql} FROM df ORDER BY "{num}" ASC LIMIT {limit}'

        # Pattern 5: Distribution / Grouping
        if mentioned_cat:
            cat = mentioned_cat[0]
            return f'SELECT "{cat}", COUNT(*) as count FROM df GROUP BY "{cat}" ORDER BY count DESC LIMIT {limit}'

        # Default fallback: preview top rows
        selected_cols = (cat_cols[:2] + num_cols[:3]) if (cat_cols or num_cols) else cols[:5]
        col_sql = ", ".join([f'"{c}"' for c in selected_cols])
        return f'SELECT {col_sql} FROM df LIMIT {limit}'

    @classmethod
    def auto_chart(cls, result_df: pd.DataFrame) -> str:
        """Determine optimal visualization chart type from result shape and dtypes."""
        n_rows, n_cols = result_df.shape
        if n_rows == 1 and n_cols == 1:
            return "kpi"
        if n_cols == 2:
            col0_dtype = result_df.iloc[:, 0].dtype
            col1_dtype = result_df.iloc[:, 1].dtype
            if pd.api.types.is_numeric_dtype(col1_dtype):
                col0_name = result_df.columns[0].lower()
                if any(k in col0_name for k in ["date", "time", "year", "month"]):
                    return "line"
                return "bar"
        if n_cols == 3 and any(pd.api.types.is_numeric_dtype(result_df[c]) for c in result_df.columns):
            return "bar"
        return "table"

    @classmethod
    def ask_data(cls, dataset_id: str, question: str, db: Session) -> Dict[str, Any]:
        """Process natural language question into SQL, execute in DuckDB, and return chart data."""
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        df = DatasetProfiler.load_dataset(dataset.file_path)
        q = question.lower().strip()
        sql = cls.generate_sql(question, df)
        intent = "query"

        # Useful broad questions are computed directly from the selected dataset.
        # This avoids pretending that a generic preview answered the question.
        if any(term in q for term in ["rows and columns", "columns and rows", "dataset shape", "how many columns"]):
            intent = "shape"
            sql = "SELECT COUNT(*) AS total_rows FROM df"
            res_df = pd.DataFrame([{"total_rows": len(df), "total_columns": len(df.columns)}])
        elif any(term in q for term in ["missing", "null value", "null values", "empty values"]):
            intent = "missing_values"
            sql = "-- Computed safely from the in-memory dataset; no data is changed."
            missing = df.isna().sum()
            res_df = pd.DataFrame({"column": missing.index, "missing_count": missing.values, "missing_rate_percent": (missing.values / max(len(df), 1) * 100).round(2)})
            res_df = res_df.sort_values("missing_count", ascending=False)
        elif any(term in q for term in ["list columns", "show columns", "column names", "what columns"]):
            intent = "schema"
            sql = "-- Dataset schema inspection; no data is changed."
            res_df = pd.DataFrame({"column": df.columns, "data_type": [str(dtype) for dtype in df.dtypes], "non_null_values": [int(df[column].notna().sum()) for column in df.columns]})
        elif any(term in q for term in ["average of numeric", "average numeric", "mean of numeric"]):
            intent = "numeric_averages"
            sql = "-- Computed averages for every numeric column."
            numeric = df.select_dtypes(include=["number"])
            if numeric.empty:
                raise ValueError("This dataset has no numeric columns to average.")
            res_df = pd.DataFrame({"column": numeric.columns, "average": numeric.mean().round(4).values})
        else:
            if not cls.validate_sql(sql):
                raise ValueError("Generated SQL violated security constraints (SELECT only).")
            try:
                con = duckdb.connect(database=":memory:")
                con.register("df", df)
                res_df = con.execute(sql).df()
            except Exception as e:
                logger.error(f"DuckDB query execution failed: {e}")
                raise ValueError(f"SQL execution error: {str(e)}")

        chart_type = cls.auto_chart(res_df)
        columns = res_df.columns.tolist()
        rows = res_df.to_dict(orient="records")

        # Clean NaN/inf
        cleaned_rows = []
        for r in rows:
            clean_r = {}
            for k, v in r.items():
                if pd.isna(v):
                    clean_r[k] = None
                elif isinstance(v, (int, float)):
                    clean_r[k] = round(float(v), 4) if isinstance(v, float) else int(v)
                else:
                    clean_r[k] = str(v)
            cleaned_rows.append(clean_r)

        if intent == "shape":
            explanation = f"This dataset contains {len(df):,} rows and {len(df.columns):,} columns."
        elif intent == "missing_values":
            total_missing = int(df.isna().sum().sum())
            affected = int((df.isna().sum() > 0).sum())
            explanation = f"Found {total_missing:,} missing value(s) across {affected} column(s). The table ranks every column by missingness."
        elif intent == "schema":
            explanation = f"The selected dataset has {len(df.columns)} columns. Types and populated row counts are shown below."
        elif intent == "numeric_averages":
            explanation = f"Computed averages for {len(res_df)} numeric column(s) in the selected dataset."
        elif len(res_df) == 1 and len(res_df.columns) == 1:
            explanation = f"{res_df.columns[0].replace('_', ' ').capitalize()}: {cls._display_value(res_df.iloc[0, 0])}."
        else:
            explanation = f"I used the selected dataset and found {len(res_df):,} result(s). Review the table or chart below."

        return {
            "question": question,
            "sql": sql,
            "chart_type": chart_type,
            # Backward-compatible UI fields.  Both chat surfaces now receive
            # an explicit chart type and axis mapping instead of guessing.
            "recommended_chart": chart_type,
            "x_axis": columns[0] if columns else None,
            "y_axis": columns[1] if len(columns) > 1 else None,
            "columns": columns,
            "rows": cleaned_rows,
            "row_count": len(cleaned_rows),
            "dataset_id": dataset_id,
            "summary": explanation,
            "explanation": explanation,
            "intent": intent,
        }
