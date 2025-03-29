from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_tasks_endpoint():
    # Test getting tasks for a user
    response = client.get("/sqldb/tasks/test_user_id")
    assert response.status_code == 200
    assert "tasks" in response.json()
    assert isinstance(response.json()["tasks"], list) 