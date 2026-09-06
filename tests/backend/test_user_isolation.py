import io
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.db.models import User, Dataset, Experiment, MLModel, TaskType, ExperimentStatus, ModelStatus
from app.core.security import hash_password, create_access_token

client = TestClient(app)


@pytest.fixture
def test_users():
    """Create two test users: Alice and Bob."""
    db: Session = SessionLocal()
    alice_id = f"test_alice_{uuid.uuid4().hex[:8]}"
    bob_id = f"test_bob_{uuid.uuid4().hex[:8]}"

    alice = User(
        id=alice_id,
        email=f"{alice_id}@example.com",
        hashed_password=hash_password("password123"),
        name="Alice Tester",
    )
    bob = User(
        id=bob_id,
        email=f"{bob_id}@example.com",
        hashed_password=hash_password("password123"),
        name="Bob Tester",
    )
    db.add_all([alice, bob])
    db.commit()

    alice_token = create_access_token({"sub": alice.id})
    bob_token = create_access_token({"sub": bob.id})

    yield {
        "alice": {"id": alice.id, "email": alice.email, "token": alice_token, "headers": {"Authorization": f"Bearer {alice_token}"}},
        "bob": {"id": bob.id, "email": bob.email, "token": bob_token, "headers": {"Authorization": f"Bearer {bob_token}"}},
    }

    # Clean up
    db.query(MLModel).filter(MLModel.user_id.in_([alice_id, bob_id])).delete(synchronize_session=False)
    db.query(Experiment).filter(Experiment.user_id.in_([alice_id, bob_id])).delete(synchronize_session=False)
    db.query(Dataset).filter(Dataset.user_id.in_([alice_id, bob_id])).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_([alice_id, bob_id])).delete(synchronize_session=False)
    db.commit()
    db.close()


def test_dataset_user_isolation(test_users):
    """Test that datasets uploaded by Alice are isolated from Bob and anonymous users."""
    alice_headers = test_users["alice"]["headers"]
    bob_headers = test_users["bob"]["headers"]
    anon_headers = {"x-anonymous": "true"}

    # 1. Alice uploads dataset
    csv_content = b"feature1,feature2,target\n1,10,1\n2,20,0\n3,30,1\n"
    file = io.BytesIO(csv_content)
    upload_resp = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("alice_dataset.csv", file, "text/csv")},
        headers=alice_headers,
    )
    assert upload_resp.status_code == 201
    alice_data = upload_resp.json()
    alice_dataset_id = alice_data["id"]
    assert alice_data["user_id"] == test_users["alice"]["id"]

    # 2. Alice lists datasets -> Alice sees alice_dataset.csv
    alice_list = client.get("/api/v1/datasets", headers=alice_headers).json()
    alice_ids = [d["id"] for d in alice_list["items"]]
    assert alice_dataset_id in alice_ids

    # 3. Bob lists datasets -> Bob DOES NOT see Alice's dataset
    bob_list = client.get("/api/v1/datasets", headers=bob_headers).json()
    bob_ids = [d["id"] for d in bob_list["items"]]
    assert alice_dataset_id not in bob_ids

    # 4. Bob tries to GET Alice's dataset -> 404 NOT FOUND
    bob_get = client.get(f"/api/v1/datasets/{alice_dataset_id}", headers=bob_headers)
    assert bob_get.status_code == 404

    # 5. Bob tries to GET preview of Alice's dataset -> 404 NOT FOUND
    bob_preview = client.get(f"/api/v1/datasets/{alice_dataset_id}/preview", headers=bob_headers)
    assert bob_preview.status_code == 404

    # 6. Bob tries to GET profile of Alice's dataset -> 404 NOT FOUND
    bob_profile = client.get(f"/api/v1/datasets/{alice_dataset_id}/profile", headers=bob_headers)
    assert bob_profile.status_code == 404

    # 7. Bob tries to DELETE Alice's dataset -> 404 NOT FOUND
    bob_delete = client.delete(f"/api/v1/datasets/{alice_dataset_id}", headers=bob_headers)
    assert bob_delete.status_code == 404

    # 8. Unauthenticated user tries to access Alice's dataset -> 401 UNAUTHORIZED
    anon_get = client.get(f"/api/v1/datasets/{alice_dataset_id}", headers=anon_headers)
    assert anon_get.status_code == 401

    # 9. Bob uploads his own dataset
    bob_csv = b"colA,colB\n5,6\n7,8\n"
    bob_file = io.BytesIO(bob_csv)
    bob_upload = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("bob_dataset.csv", bob_file, "text/csv")},
        headers=bob_headers,
    )
    assert bob_upload.status_code == 201
    bob_dataset_id = bob_upload.json()["id"]

    # 10. Verify bidirectional isolation
    alice_list_after = client.get("/api/v1/datasets", headers=alice_headers).json()
    alice_ids_after = [d["id"] for d in alice_list_after["items"]]
    assert alice_dataset_id in alice_ids_after
    assert bob_dataset_id not in alice_ids_after

    bob_list_after = client.get("/api/v1/datasets", headers=bob_headers).json()
    bob_ids_after = [d["id"] for d in bob_list_after["items"]]
    assert bob_dataset_id in bob_ids_after
    assert alice_dataset_id not in bob_ids_after


def test_model_and_experiment_user_isolation(test_users):
    """Test that models and experiments created by Alice are completely isolated from Bob."""
    alice_headers = test_users["alice"]["headers"]
    bob_headers = test_users["bob"]["headers"]

    db: Session = SessionLocal()

    # Create dataset for Alice
    alice_dataset = Dataset(
        id=f"ds_{uuid.uuid4().hex[:8]}",
        user_id=test_users["alice"]["id"],
        original_filename="alice_train.csv",
        stored_filename="alice_train.csv",
        file_path="fake_path.csv",
        file_size=100,
        file_type="CSV",
    )
    db.add(alice_dataset)

    # Create completed experiment for Alice
    exp_id = f"exp_{uuid.uuid4().hex[:8]}"
    alice_exp = Experiment(
        id=exp_id,
        name="Random Forest Classifier",
        user_id=test_users["alice"]["id"],
        dataset_id=alice_dataset.id,
        target_column="target",
        task_type=TaskType.BINARY_CLASSIFICATION,
        algorithm="random_forest",
        metrics=json.dumps({"accuracy": 0.95, "f1": 0.94}),
        status=ExperimentStatus.COMPLETED,
    )
    db.add(alice_exp)

    # Create registered model for Alice
    model_id = f"mod_{uuid.uuid4().hex[:8]}"
    alice_model = MLModel(
        id=model_id,
        name="Alice Churn Model",
        version=1,
        user_id=test_users["alice"]["id"],
        experiment_id=alice_exp.id,
        dataset_id=alice_dataset.id,
        task_type=TaskType.BINARY_CLASSIFICATION,
        target_column="target",
        algorithm="random_forest",
        artifact_path="fake_model.joblib",
        metrics=json.dumps({"accuracy": 0.95}),
        status=ModelStatus.TRAINED,
    )
    db.add(alice_model)
    db.commit()
    db.close()

    # 1. Alice lists models -> Alice sees Alice's model
    alice_models_resp = client.get("/api/v1/models", headers=alice_headers)
    assert alice_models_resp.status_code == 200
    alice_model_ids = [m["id"] for m in alice_models_resp.json()["items"]]
    assert model_id in alice_model_ids

    # 2. Bob lists models -> Bob DOES NOT see Alice's model
    bob_models_resp = client.get("/api/v1/models", headers=bob_headers)
    assert bob_models_resp.status_code == 200
    bob_model_ids = [m["id"] for m in bob_models_resp.json()["items"]]
    assert model_id not in bob_model_ids

    # 3. Bob attempts to get Alice's model directly -> 404 NOT FOUND
    bob_get_model = client.get(f"/api/v1/models/{model_id}", headers=bob_headers)
    assert bob_get_model.status_code == 404

    # 4. Bob attempts to get model card -> 404 NOT FOUND
    bob_get_card = client.get(f"/api/v1/models/{model_id}/card", headers=bob_headers)
    assert bob_get_card.status_code == 404

    # 5. Bob attempts to predict using Alice's model -> 404 NOT FOUND
    bob_predict = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"f1": 1, "f2": 2}},
        headers=bob_headers,
    )
    assert bob_predict.status_code == 404

    # 6. Bob attempts to get Alice's experiment -> 404 NOT FOUND
    bob_get_exp = client.get(f"/api/v1/experiments/{exp_id}", headers=bob_headers)
    assert bob_get_exp.status_code == 404

    # 7. Bob lists experiments -> Alice's experiment is not visible to Bob
    bob_exp_list = client.get("/api/v1/experiments", headers=bob_headers).json()
    bob_exp_ids = [e["id"] for e in bob_exp_list]
    assert exp_id not in bob_exp_ids

    # 8. Dashboard statistics are isolated
    alice_dash = client.get("/api/v1/models/dashboard", headers=alice_headers).json()
    assert alice_dash["models"] >= 1
    assert alice_dash["datasets"] >= 1

    bob_dash = client.get("/api/v1/models/dashboard", headers=bob_headers).json()
    assert bob_dash["models"] == 0
    assert bob_dash["datasets"] == 0
