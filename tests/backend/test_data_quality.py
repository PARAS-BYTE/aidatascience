import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_data_quality_and_parquet_support():
    # 1. Register & login
    email = "data_quality_tester@aidatascience.local"
    password = "QualityPassword123!"

    client.post(
        "/api/v1/auth/register",
        json={"name": "DQ Tester", "email": email, "password": password}
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create DataFrame with intentional quality issues and save as Parquet
    df = pd.DataFrame({
        "customer_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10], # duplicate row 10
        "age": [25, 34, 45, -5, 52, 60, 29, 38, 250, 42, 42], # negative age & 250 outlier
        "country": ["United States", "united states", "United States", "United State", "Canada", "Canada", "Canada", "Germany", "Germany", "France", "France"], # fuzzy variants
        "income": [50000.0, 62000.0, None, 80000.0, None, 95000.0, 48000.0, 71000.0, 120000.0, 68000.0, 68000.0], # missing values
        "churn": [0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0], # target
        "leaked_target_flag": [0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0], # 100% correlation target leak
    })

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)

    # 3. Upload Parquet Dataset
    files = {"file": ("customer_churn.parquet", parquet_buffer, "application/octet-stream")}
    upload_res = client.post("/api/v1/datasets/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    dataset = upload_res.json()
    dataset_id = dataset["id"]
    assert dataset["file_type"] == "PARQUET"

    # 4. Assess Data Quality
    assess_res = client.post(
        f"/api/v1/datasets/{dataset_id}/data-quality/assess",
        json={"target_column": "churn"},
        headers=headers,
    )
    assert assess_res.status_code == 200
    dq_data = assess_res.json()

    # Verify quality dimensions
    assert "overall_score" in dq_data
    assert 0 <= dq_data["overall_score"] <= 100
    dims = dq_data["dimensions"]

    # Target leakage verification
    assert "leakage_risk" in dims
    assert "leaked_target_flag" in dims["leakage_risk"]["high_risk_columns"]

    # Fuzzy categorical consistency verification
    assert "consistency" in dims
    assert dims["consistency"]["inconsistent_categories"] >= 1

    # Completeness verification
    assert "completeness" in dims
    assert dims["completeness"]["total_missing"] == 2

    # Validity verification (negative age)
    assert "validity" in dims
    assert dims["validity"]["semantic_violations_count"] >= 1

    # Recommendations verification
    recs = dq_data["recommendations"]
    assert len(recs) > 0
    rec_actions = [r["suggested_fix"] for r in recs]
    assert "drop_column" in rec_actions

    # 5. Execute Automated Remediation
    remediate_res = client.post(
        f"/api/v1/datasets/{dataset_id}/data-quality/remediate",
        json={
            "drop_columns": ["leaked_target_flag"],
            "remove_duplicates": True,
            "impute_missing": True,
            "standardize_fuzzy": True,
        },
        headers=headers,
    )
    assert remediate_res.status_code == 200
    rem_data = remediate_res.json()
    assert rem_data["success"] is True
    assert rem_data["new_version"] == 2
    # Quality score should improve after remediation
    assert rem_data["new_overall_score"] >= dq_data["overall_score"]
