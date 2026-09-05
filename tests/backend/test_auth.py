import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_auth_register_and_login():
    email = "testuser_unique@aidatascience.local"
    password = "secretpassword123"

    # 1. Register new user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"name": "Test Scientist", "email": email, "password": password, "bio": "Data tester"}
    )
    assert reg_resp.status_code in (201, 400)
    
    # 2. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == email
    token = login_data["access_token"]

    # 3. Access /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email

    # 4. Access /auth/profile summary
    profile_resp = client.get("/api/v1/auth/profile", headers=headers)
    assert profile_resp.status_code == 200
    profile_data = profile_resp.json()
    assert "stats" in profile_data
    assert "uploaded_datasets" in profile_data
    assert "trained_models" in profile_data
    assert "recent_activities" in profile_data
