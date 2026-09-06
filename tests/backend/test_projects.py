import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_projects_and_dataset_versioning_flow():
    # 1. Register & login
    email = "project_test_user@aidatascience.local"
    password = "ProjectPassword123!"

    client.post(
        "/api/v1/auth/register",
        json={"name": "Project Tester", "email": email, "password": password}
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Project
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Customer Churn Prediction", "description": "Predicting customer churn"},
        headers=headers,
    )
    assert proj_res.status_code == 201
    project_data = proj_res.json()
    assert project_data["name"] == "Customer Churn Prediction"
    project_id = project_data["id"]

    # 3. List Projects
    list_res = client.get("/api/v1/projects", headers=headers)
    assert list_res.status_code == 200
    projects = list_res.json()["items"]
    assert any(p["id"] == project_id for p in projects)

    # 4. Get Project Details & Stats
    get_res = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_res.status_code == 200
    proj_stats = get_res.json()
    assert proj_stats["name"] == "Customer Churn Prediction"
    assert proj_stats["datasets"] == 0

    # 5. Upload Dataset assigned to Project
    csv_content = (
        "id,age,tenure,balance,churn\n"
        "1,25,1,1000.5,0\n"
        "2,45,5,54000.0,1\n"
        "3,35,3,23000.2,0\n"
        "4,52,8,94000.8,1\n"
        "5,23,2,500.0,0\n"
    )
    files = {"file": ("churn.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files=files,
        headers=headers,
    )
    assert upload_res.status_code == 201
    dataset = upload_res.json()
    dataset_id = dataset["id"]
    assert dataset["project_id"] == project_id
    assert dataset["version"] == 1

    # 6. Verify Dataset Version 1 was created
    ver_res = client.get(f"/api/v1/datasets/{dataset_id}/versions", headers=headers)
    assert ver_res.status_code == 200
    ver_data = ver_res.json()
    assert ver_data["current_version"] == 1
    assert len(ver_data["versions"]) >= 1
    assert ver_data["versions"][0]["version"] == 1
    assert ver_data["versions"][0]["change_summary"] == "Initial upload"

    # 7. Clean Dataset and Verify Version Bump to 2
    clean_res = client.post(
        f"/api/v1/datasets/{dataset_id}/clean",
        json={
            "target": "churn",
            "drop_ids": True,
            "drop_constants": True,
            "remove_duplicates": True,
            "handle_missing": "mean",
        },
        headers=headers,
    )
    assert clean_res.status_code == 200

    # Check updated versions
    ver_res2 = client.get(f"/api/v1/datasets/{dataset_id}/versions", headers=headers)
    assert ver_res2.status_code == 200
    ver_data2 = ver_res2.json()
    assert ver_data2["current_version"] == 2
    assert len(ver_data2["versions"]) == 2

    # 8. Check Project Datasets Endpoint
    proj_ds_res = client.get(f"/api/v1/projects/{project_id}/datasets", headers=headers)
    assert proj_ds_res.status_code == 200
    proj_datasets = proj_ds_res.json()
    assert proj_datasets["total"] == 1
    assert proj_datasets["items"][0]["id"] == dataset_id

    # 9. Check Project Activity Endpoint
    act_res = client.get(f"/api/v1/projects/{project_id}/activity", headers=headers)
    assert act_res.status_code == 200

    # 10. Update Project
    update_res = client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "Churn Prediction V2", "description": "Updated description"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Churn Prediction V2"

    # 11. Delete Project
    del_res = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert del_res.status_code == 200
