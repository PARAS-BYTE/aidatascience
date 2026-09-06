import io
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app
from ml_engine.unsupervised.unsupervised_engine import UnsupervisedEngine

client = TestClient(app)


def test_unsupervised_clustering_engine():
    np.random.seed(42)
    # Generate 3 distinct synthetic clusters
    c1 = np.random.normal(loc=10, scale=1.5, size=(40, 3))
    c2 = np.random.normal(loc=30, scale=1.5, size=(40, 3))
    c3 = np.random.normal(loc=60, scale=1.5, size=(40, 3))

    data = np.vstack([c1, c2, c3])
    df = pd.DataFrame(data, columns=["feature_1", "feature_2", "feature_3"])

    # 1. K-Means with Auto-K
    kmeans_res = UnsupervisedEngine.run_clustering(
        df=df,
        algorithm="kmeans",
        auto_k=True,
        k_min=2,
        k_max=5,
    )
    assert "error" not in kmeans_res
    assert kmeans_res["optimal_k"] == 3  # Should identify exactly 3 clusters
    assert kmeans_res["metrics"]["silhouette_score"] > 0.6  # High separation
    assert kmeans_res["metrics"]["cluster_separation_rating"] == "Strong"
    assert len(kmeans_res["pca_projection"]["points"]) == 120
    assert len(kmeans_res["cluster_personas"]) == 3

    # Check personas content
    for persona in kmeans_res["cluster_personas"]:
        assert "title" in persona
        assert "distinctive_traits" in persona
        assert persona["count"] > 0

    # 2. GMM Clustering
    gmm_res = UnsupervisedEngine.run_clustering(
        df=df,
        algorithm="gmm",
        auto_k=False,
        n_clusters=3,
    )
    assert "error" not in gmm_res
    assert gmm_res["optimal_k"] == 3

    # 3. Agglomerative Clustering
    agg_res = UnsupervisedEngine.run_clustering(
        df=df,
        algorithm="agglomerative",
        auto_k=False,
        n_clusters=3,
    )
    assert "error" not in agg_res
    assert agg_res["optimal_k"] == 3


def test_unsupervised_anomaly_detection_engine():
    np.random.seed(42)
    # Generate normal records + 5 extreme outliers
    normal_data = np.random.normal(loc=50, scale=5, size=(100, 2))
    outliers = np.array([
        [150.0, 150.0],
        [160.0, 140.0],
        [145.0, 155.0],
        [-50.0, -40.0],
        [-60.0, -50.0],
    ])
    df = pd.DataFrame(np.vstack([normal_data, outliers]), columns=["metric_x", "metric_y"])

    # 1. Isolation Forest
    iso_res = UnsupervisedEngine.detect_anomalies(
        df=df,
        algorithm="isolation_forest",
        contamination=0.05,
    )
    assert "error" not in iso_res
    assert iso_res["anomaly_count"] >= 5
    assert iso_res["status"] == "Anomalies Identified"
    assert len(iso_res["top_anomalies"]) > 0
    assert len(iso_res["anomaly_flags"]) == 105

    # Check that the extreme outliers are in the top anomalies
    top_indices = [a["row_index"] for a in iso_res["top_anomalies"]]
    # At least 3 of our 5 outliers (indices 100..104) should be ranked in top anomalies
    found_outliers = sum(1 for idx in top_indices if idx >= 100)
    assert found_outliers >= 3

    # 2. Local Outlier Factor (LOF)
    lof_res = UnsupervisedEngine.detect_anomalies(
        df=df,
        algorithm="lof",
        contamination=0.05,
    )
    assert "error" not in lof_res
    assert lof_res["anomaly_count"] >= 3


def test_unsupervised_pca_engine():
    np.random.seed(42)
    # 4 correlated features
    x1 = np.linspace(1, 100, 80)
    x2 = 2 * x1 + np.random.normal(0, 2, 80)
    x3 = -1.5 * x1 + np.random.normal(0, 3, 80)
    x4 = np.random.normal(10, 5, 80)

    df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4})

    pca_res = UnsupervisedEngine.run_pca(df=df, n_components=2)
    assert pca_res["n_components"] == 2
    assert pca_res["total_variance_explained"] > 70.0
    assert len(pca_res["points"]) == 80
    assert "PC1" in pca_res["feature_loadings"]
    assert "PC2" in pca_res["feature_loadings"]


def test_unsupervised_api_endpoints_and_augmentation():
    # 1. Authenticate test user
    email = "unsupervised_tester_unique@aidatascience.local"
    pwd = "ProjectPassword123!"
    client.post("/api/v1/auth/register", json={"name": "Unsupervised Tester", "email": email, "password": pwd})
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload test CSV
    csv_content = (
        "feature_a,feature_b,category\n"
        "10.5,20.1,A\n"
        "11.2,19.8,A\n"
        "10.8,20.4,A\n"
        "50.2,80.1,B\n"
        "51.0,81.4,B\n"
        "49.8,79.9,B\n"
        "90.1,10.2,C\n"
        "91.5,11.0,C\n"
        "89.7,10.5,C\n"
        "90.8,11.2,C\n"
    )
    files = {"file": ("unsupervised_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]
    assert upload_res.json().get("version", 1) == 1

    # 3. Test Clustering Endpoint
    cluster_res = client.post(
        f"/api/v1/datasets/{dataset_id}/unsupervised/cluster",
        json={"algorithm": "kmeans", "auto_k": True, "k_min": 2, "k_max": 4},
        headers=headers,
    )
    assert cluster_res.status_code == 200
    cluster_data = cluster_res.json()
    assert cluster_data["optimal_k"] in (2, 3)
    assert len(cluster_data["cluster_labels"]) == 10

    # 4. Test Anomaly Endpoint
    anomaly_res = client.post(
        f"/api/v1/datasets/{dataset_id}/unsupervised/anomalies",
        json={"algorithm": "isolation_forest", "contamination": 0.1},
        headers=headers,
    )
    assert anomaly_res.status_code == 200
    anomaly_data = anomaly_res.json()
    assert len(anomaly_data["anomaly_flags"]) == 10

    # 5. Test PCA Endpoint
    pca_res = client.post(
        f"/api/v1/datasets/{dataset_id}/unsupervised/pca",
        json={"n_components": 2},
        headers=headers,
    )
    assert pca_res.status_code == 200
    assert pca_res.json()["n_components"] == 2

    # 6. Test Augment Column & Version Bump Endpoint
    append_res = client.post(
        f"/api/v1/datasets/{dataset_id}/unsupervised/append-labels",
        json={
            "column_name": "cluster_segment",
            "values": cluster_data["cluster_labels"],
            "change_summary": "Appended KMeans cluster segments",
        },
        headers=headers,
    )
    assert append_res.status_code == 200
    append_data = append_res.json()
    assert append_data["success"] is True
    assert append_data["new_version"] == 2
    assert append_data["appended_column"] == "cluster_segment"

    # 7. Verify Dataset Version History
    versions_res = client.get(f"/api/v1/datasets/{dataset_id}/versions", headers=headers)
    assert versions_res.status_code == 200
    versions = versions_res.json()["versions"]
    assert len(versions) >= 2
    latest_version = versions[0]
    assert latest_version["version"] == 2
    assert "KMeans cluster" in latest_version["change_summary"]
