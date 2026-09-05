import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "backend"


def test_upload_valid_csv():
    """Test uploading a valid CSV file."""
    csv_content = b"name,age,city\nAlice,30,New York\nBob,25,London\n"
    file = io.BytesIO(csv_content)
    
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("test_data.csv", file, "text/csv")}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "test_data.csv"
    assert data["file_type"] == "CSV"
    assert data["upload_status"] == "SUCCESS"
    assert "id" in data

    # Clean up created dataset
    dataset_id = data["id"]
    del_resp = client.delete(f"/api/v1/datasets/{dataset_id}")
    assert del_resp.status_code == 200


def test_upload_invalid_file_extension():
    """Test uploading an unsupported file format (e.g. .txt or .exe)."""
    file_content = b"Invalid file contents"
    file = io.BytesIO(file_content)

    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("malicious.exe", file, "application/octet-stream")}
    )

    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file format" in data["detail"]


def test_dataset_list_and_delete():
    """Test dataset listing and deletion lifecycle."""
    # 1. Upload dataset
    csv_content = b"col1,col2\n1,2\n3,4\n"
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sample.csv", io.BytesIO(csv_content), "text/csv")}
    )
    dataset_id = response.json()["id"]

    # 2. List datasets
    list_resp = client.get("/api/v1/datasets")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert any(d["id"] == dataset_id for d in items)

    # 3. Delete dataset
    delete_resp = client.delete(f"/api/v1/datasets/{dataset_id}")
    assert delete_resp.status_code == 200

    # 4. Verify dataset no longer exists
    get_resp = client.get(f"/api/v1/datasets/{dataset_id}")
    assert get_resp.status_code == 404


def test_job_system():
    """Test triggering a test background job and listing jobs."""
    # Trigger job
    response = client.post("/api/v1/jobs/test")
    assert response.status_code == 202
    job_data = response.json()
    job_id = job_data["id"]
    assert job_data["status"] in ["QUEUED", "PENDING", "RUNNING"]

    # Get job status
    job_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["id"] == job_id

    # List jobs
    list_resp = client.get("/api/v1/jobs")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1


def test_dataset_preview_endpoint():
    """Test GET /api/v1/datasets/{id}/preview with pagination, search, and sorting."""
    csv_content = b"name,age,salary,department\nAlice,30,70000,Engineering\nBob,25,50000,Marketing\nCharlie,35,90000,Engineering\nDiana,28,60000,HR\n"
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("employees.csv", io.BytesIO(csv_content), "text/csv")}
    )
    assert response.status_code == 201
    dataset_id = response.json()["id"]

    try:
        # 1. Basic preview
        prev_resp = client.get(f"/api/v1/datasets/{dataset_id}/preview?limit=2&offset=0")
        assert prev_resp.status_code == 200
        prev_data = prev_resp.json()
        assert prev_data["total_rows"] == 4
        assert prev_data["total_columns"] == 4
        assert len(prev_data["rows"]) == 2
        assert "name" in prev_data["columns"]
        assert "age" in prev_data["columns"]

        # 2. Search filtering
        search_resp = client.get(f"/api/v1/datasets/{dataset_id}/preview?search=Engineering")
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert len(search_data["rows"]) == 2

        # 3. Sorting
        sort_resp = client.get(f"/api/v1/datasets/{dataset_id}/preview?sort_col=age&sort_dir=desc")
        assert sort_resp.status_code == 200
        sort_data = sort_resp.json()
        assert sort_data["rows"][0]["name"] == "Charlie"
    finally:
        client.delete(f"/api/v1/datasets/{dataset_id}")


def test_agent_universal_charts_and_preview():
    """Test AI Agent generating box plots, radar charts, donut charts, and CSV head preview."""
    csv_content = b"category,metric1,metric2,metric3,group\nA,10,20,30,X\nB,15,25,35,Y\nA,12,22,32,X\nB,18,28,38,Y\nC,20,30,40,X\n"
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("metrics.csv", io.BytesIO(csv_content), "text/csv")}
    )
    assert response.status_code == 201
    dataset_id = response.json()["id"]

    try:
        # 1. Preview CSV head in chat
        chat1 = client.post("/api/v1/agent/chat", json={
            "message": "Show head of csv",
            "dataset_id": dataset_id,
        })
        assert chat1.status_code == 200
        d1 = chat1.json()
        assert len(d1["charts"]) > 0
        assert d1["charts"][0]["type"] == "table"

        # 2. Box plot
        chat2 = client.post("/api/v1/agent/chat", json={
            "message": "Generate a box plot of metric1",
            "dataset_id": dataset_id,
        })
        assert chat2.status_code == 200
        d2 = chat2.json()
        assert len(d2["charts"]) > 0
        assert d2["charts"][0]["type"] == "boxplot"
        assert "min" in d2["charts"][0]["data"][0]
        assert "median" in d2["charts"][0]["data"][0]

        # 3. Donut chart
        chat3 = client.post("/api/v1/agent/chat", json={
            "message": "Create a donut chart of category",
            "dataset_id": dataset_id,
        })
        assert chat3.status_code == 200
        d3 = chat3.json()
        assert len(d3["charts"]) > 0
        assert d3["charts"][0]["type"] == "donut"

        # 4. Radar chart
        chat4 = client.post("/api/v1/agent/chat", json={
            "message": "Plot a radar chart of features",
            "dataset_id": dataset_id,
        })
        assert chat4.status_code == 200
        d4 = chat4.json()
        assert len(d4["charts"]) > 0
        assert d4["charts"][0]["type"] == "radar"
    finally:
        client.delete(f"/api/v1/datasets/{dataset_id}")


def test_auto_pilot_pipeline():
    """Test the autonomous end-to-end AI Auto-Pilot pipeline."""
    # Generate CSV dataset
    rows = ["feature1,feature2,feature3,target"]
    for i in range(40):
        f1 = i * 1.5
        f2 = (i % 5) * 2.0
        f3 = i * 0.2
        t = 1 if (f1 + f2) > 25 else 0
        rows.append(f"{f1},{f2},{f3},{t}")
    csv_bytes = "\n".join(rows).encode("utf-8")

    upload_resp = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("autopilot_test.csv", io.BytesIO(csv_bytes), "text/csv")}
    )
    assert upload_resp.status_code == 201
    dataset_id = upload_resp.json()["id"]

    try:
        # Run Auto-Pilot pipeline
        ap_resp = client.post("/api/v1/agent/auto-pilot", json={
            "dataset_id": dataset_id,
            "target": "target",
            "enable_feature_engineering": True,
            "cv_folds": 3,
            "max_interactions": 3,
        })
        assert ap_resp.status_code == 200
        data = ap_resp.json()

        assert data["status"] == "success"
        assert data["dataset_id"] == dataset_id
        assert data["target_column"] == "target"
        assert len(data["steps"]) == 6
        assert data["steps"][0]["title"] == "Dataset Intelligence & Target Detection"
        assert data["steps"][4]["title"] == "AutoML Training & Leaderboard"
        assert data["best_model"] is not None
        assert "name" in data["best_model"]
        assert len(data["leaderboard"]) > 0
        assert len(data["charts"]) > 0
        assert "Autonomous AI Auto-Pilot Pipeline Complete" in data["executive_summary"]

        # Also test conversational auto-pilot invocation
        chat_resp = client.post("/api/v1/agent/chat", json={
            "message": "Run AI Auto-Pilot pipeline on this dataset",
            "dataset_id": dataset_id,
        })
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        assert "Auto-Pilot Pipeline Complete" in chat_data["response"]
        assert any(tc["tool"] == "auto_pilot_pipeline" for tc in chat_data.get("tool_calls", []))
    finally:
        client.delete(f"/api/v1/datasets/{dataset_id}")


