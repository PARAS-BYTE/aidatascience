import io
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app
from ml_engine.analysis.statistical_engine import StatisticalEngine

client = TestClient(app)


def test_statistical_engine_methods():
    np.random.seed(42)

    # 1. Test Normality
    normal_data = pd.Series(np.random.normal(loc=50, scale=10, size=200), name="normal_col")
    norm_res = StatisticalEngine.test_normality(normal_data)
    assert norm_res["is_normal"] is True
    assert norm_res["p_value"] >= 0.05
    assert "Normally distributed" in norm_res["interpretation"]

    skewed_data = pd.Series(np.random.exponential(scale=2.0, size=200), name="skewed_col")
    skew_res = StatisticalEngine.test_normality(skewed_data)
    assert skew_res["is_normal"] is False
    assert skew_res["p_value"] < 0.05

    # 2. Test 2-Group Comparison (t-test / Cohen's d)
    num_vals = pd.Series(list(np.random.normal(20, 3, 50)) + list(np.random.normal(35, 3, 50)), name="age")
    cat_vals = pd.Series(["No"] * 50 + ["Yes"] * 50, name="churn")
    two_grp = StatisticalEngine.test_numerical_vs_categorical(num_vals, cat_vals)
    assert two_grp["test_type"] == "two_sample_comparison"
    assert two_grp["is_significant"] is True
    assert two_grp["p_value"] < 0.001
    assert two_grp["effect_size"]["metric"] == "Cohen's d"
    assert abs(two_grp["effect_size"]["value"]) > 0.8  # Large effect

    # 3. Test 3+ Group Comparison (ANOVA / Eta-squared)
    num_vals_multi = pd.Series(
        list(np.random.normal(10, 2, 40)) + list(np.random.normal(20, 2, 40)) + list(np.random.normal(30, 2, 40)),
        name="salary"
    )
    cat_vals_multi = pd.Series(["Tier1"] * 40 + ["Tier2"] * 40 + ["Tier3"] * 40, name="tier")
    multi_grp = StatisticalEngine.test_numerical_vs_categorical(num_vals_multi, cat_vals_multi)
    assert multi_grp["test_type"] == "multigroup_comparison"
    assert multi_grp["is_significant"] is True
    assert multi_grp["effect_size"]["metric"] == "Eta-squared"

    # 4. Test Chi-Squared
    cat_a = pd.Series(["A"] * 40 + ["B"] * 40, name="department")
    cat_b = pd.Series(["Yes"] * 35 + ["No"] * 5 + ["Yes"] * 5 + ["No"] * 35, name="promoted")
    chi_res = StatisticalEngine.test_categorical_vs_categorical(cat_a, cat_b)
    assert chi_res["is_significant"] is True
    assert chi_res["effect_size"]["metric"] == "Cramer's V"

    # 5. Test Correlation
    x = pd.Series(np.linspace(1, 100, 80), name="experience")
    y = pd.Series(np.linspace(20, 200, 80) + np.random.normal(0, 5, 80), name="salary")
    corr_res = StatisticalEngine.test_numerical_vs_numerical(x, y)
    assert corr_res["pearson"]["is_significant"] is True
    assert corr_res["pearson"]["r"] > 0.9

    # 6. Test Smart Chart Recommender
    test_df = pd.DataFrame({"age": num_vals, "churn": cat_vals, "salary": y[:100]})
    chart_rec = StatisticalEngine.recommend_charts(test_df, "age", "churn")
    assert chart_rec["primary_chart"] == "grouped_box_plot"


def test_statistical_endpoints_api_flow():
    # 1. Register & login
    email = "stats_tester@aidatascience.local"
    password = "StatsPassword123!"

    client.post(
        "/api/v1/auth/register",
        json={"name": "Stats Tester", "email": email, "password": password}
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload dataset
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "age": np.random.normal(40, 10, n),
        "tenure": np.random.randint(1, 10, n),
        "balance": np.random.exponential(20000, n),
        "tier": np.random.choice(["Silver", "Gold", "Platinum"], n),
        "churn": np.random.choice([0, 1], n, p=[0.7, 0.3]),
    })
    csv_buf = io.BytesIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    files = {"file": ("stats_test.csv", csv_buf, "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]

    # 3. Test GET /statistical-tests (battery)
    battery_res = client.get(
        f"/api/v1/datasets/{dataset_id}/statistical-tests?target=churn",
        headers=headers,
    )
    assert battery_res.status_code == 200
    b_data = battery_res.json()
    assert "hypothesis_battery" in b_data
    assert "tests" in b_data["hypothesis_battery"]
    assert len(b_data["hypothesis_battery"]["tests"]) > 0
    assert "executive_narrative" in b_data["hypothesis_battery"]
    assert "normality_tests" in b_data

    # 4. Test GET /statistical-tests pairwise
    pair_res = client.get(
        f"/api/v1/datasets/{dataset_id}/statistical-tests?column_a=age&column_b=churn",
        headers=headers,
    )
    assert pair_res.status_code == 200
    p_data = pair_res.json()
    assert "statistic" in p_data
    assert "p_value" in p_data

    # 5. Test GET /chart-recommendation
    chart_res = client.get(
        f"/api/v1/datasets/{dataset_id}/chart-recommendation?column_a=age&column_b=churn",
        headers=headers,
    )
    assert chart_res.status_code == 200
    c_data = chart_res.json()
    assert "primary_chart" in c_data

    # 6. Test GET /auto-eda-report
    report_res = client.get(
        f"/api/v1/datasets/{dataset_id}/auto-eda-report?target=churn",
        headers=headers,
    )
    assert report_res.status_code == 200
    rep_data = report_res.json()
    assert "markdown_report" in rep_data
    assert "# Comprehensive Automated EDA Report" in rep_data["markdown_report"]
    assert "summary" in rep_data
