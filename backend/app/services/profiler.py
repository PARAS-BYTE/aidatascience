import re
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from fastapi import HTTPException, status
from app.core.logging import logger


class DatasetProfiler:
    @staticmethod
    def load_dataset(file_path: str) -> pd.DataFrame:
        """Reads CSV or Excel dataset into a Pandas DataFrame."""
        try:
            if file_path.endswith('.csv'):
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='latin1')
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported file extension. Only CSV, XLSX, and XLS files are supported.",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading file '{file_path}': {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to read the uploaded dataset. Please verify that the file is valid and uncorrupted.",
            )

        if df is None or df.empty or df.shape[1] == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset is empty or contains zero columns.",
            )

        return df

    @staticmethod
    def detect_column_type(col_name: str, series: pd.Series) -> str:
        """Categorizes column into: numerical, categorical, date, boolean, or other."""
        s_valid = series.dropna()
        if s_valid.empty:
            return "other"

        # 1. Boolean check
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        
        # Check if values are boolean-like
        unique_vals = set(s_valid.unique())
        str_vals = {str(v).strip().lower() for v in unique_vals}
        if str_vals.issubset({"true", "false", "1", "0", "1.0", "0.0", "yes", "no", "y", "n"}):
            if len(str_vals) <= 2:
                return "boolean"

        # 2. Date check
        if pd.api.types.is_datetime64_any_dtype(series):
            return "date"

        # Conservative date check for object/string columns
        if series.dtype == "object" or pd.api.types.is_string_dtype(series):
            sample = s_valid.astype(str).head(100)
            # Must contain date separators or month names to avoid treating numbers like '100' or names as dates
            date_char_match = sample.str.contains(r"[-/\.:\s]", regex=True).mean()
            if date_char_match > 0.5:
                try:
                    converted = pd.to_datetime(sample, errors='coerce', format='mixed')
                    success_rate = converted.notna().mean()
                    if success_rate >= 0.8:
                        return "date"
                except Exception:
                    pass

        # 3. Numerical check
        if pd.api.types.is_numeric_dtype(series):
            return "numerical"

        # 4. Categorical check
        unique_count = s_valid.nunique()
        total_count = len(s_valid)
        if unique_count <= 50 or (total_count > 0 and (unique_count / total_count) < 0.5):
            return "categorical"

        return "other"

    @staticmethod
    def is_potential_id(col_name: str, series: pd.Series, rows: int) -> bool:
        """Heuristic for identifying columns that represent unique identifiers."""
        if rows == 0:
            return False

        col_clean = str(col_name).strip().lower()
        non_null_count = series.count()
        unique_count = series.nunique(dropna=True)
        unique_ratio = unique_count / rows

        # Name signals
        name_signal = (
            col_clean.endswith("id")
            or "_id_" in col_clean
            or col_clean.startswith("id_")
            or col_clean == "id"
            or col_clean.endswith("_id")
            or col_clean.endswith("code")
            or col_clean.endswith("number")
            or col_clean.endswith("num")
        )

        # High uniqueness signal (excluding floats)
        high_uniqueness_signal = (
            unique_ratio >= 0.95
            and non_null_count == rows
            and not pd.api.types.is_float_dtype(series)
        )

        return bool(name_signal or high_uniqueness_signal)

    @classmethod
    def profile_dataset(cls, file_path: str, dataset_id: str = "", filename: str = "") -> Dict[str, Any]:
        """Calculates comprehensive dataset metrics and profiling statistics."""
        df = cls.load_dataset(file_path)
        rows, cols = df.shape
        total_cells = rows * cols

        # Missing values calculation
        missing_cells = int(df.isna().sum().sum())
        missing_pct = round((missing_cells / total_cells) * 100, 2) if total_cells > 0 else 0.0

        # Duplicate calculation
        duplicates = int(df.duplicated().sum())
        duplicate_pct = round((duplicates / rows) * 100, 2) if rows > 0 else 0.0

        # Column-by-column profiling
        columns_profile: List[Dict[str, Any]] = []
        type_counts = {"numerical": 0, "categorical": 0, "date": 0, "boolean": 0, "other": 0}
        potential_ids: List[str] = []

        for col_name in df.columns:
            series = df[col_name]
            detected_type = cls.detect_column_type(str(col_name), series)
            type_counts[detected_type] = type_counts.get(detected_type, 0) + 1

            col_missing = int(series.isna().sum())
            col_missing_pct = round((col_missing / rows) * 100, 2) if rows > 0 else 0.0

            col_unique = int(series.nunique(dropna=True))
            col_unique_pct = round((col_unique / rows) * 100, 2) if rows > 0 else 0.0

            # Sample value
            valid_s = series.dropna()
            sample_val = str(valid_s.iloc[0]) if not valid_s.empty else None

            # Potential ID check
            if cls.is_potential_id(str(col_name), series, rows):
                potential_ids.append(str(col_name))

            columns_profile.append({
                "name": str(col_name),
                "dtype": str(series.dtype),
                "detected_type": detected_type,
                "missing_count": col_missing,
                "missing_percentage": col_missing_pct,
                "unique_count": col_unique,
                "unique_percentage": col_unique_pct,
                "sample_value": sample_val,
            })

        return {
            "dataset_id": dataset_id,
            "filename": filename,
            "overview": {
                "rows": rows,
                "columns": cols,
            },
            "column_types": type_counts,
            "data_quality": {
                "missing_cells": missing_cells,
                "missing_percentage": missing_pct,
                "duplicates": duplicates,
                "duplicate_percentage": duplicate_pct,
            },
            "potential_ids": potential_ids,
            "columns": columns_profile,
        }
