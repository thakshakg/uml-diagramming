import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Adjust the import path according to your project structure
from .main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API Gateway"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("gateway.main.forward_request", new_callable=AsyncMock)
def test_get_diagrams_success(mock_forward_request):
    # Mock the response from the diagram service
    mock_diagram_data = [
        {
            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "name": "Test Diagram 1",
            "owner_id": "a2c0d8e0-4f39-4b69-995a-13b8b84d2de3",
            "payload_url": "s3://mock-bucket/diagram1.json",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ]
    mock_forward_request.return_value = mock_diagram_data

    response = client.get("/diagrams")

    assert response.status_code == 200
    json_response = response.json()
    # If mock_forward_request.return_value is correctly processed by Pydantic response_model,
    # the serialized JSON output should match the mock_diagram_data if formats are identical.
    assert json_response == mock_diagram_data
    mock_forward_request.assert_called_once_with(method="GET", path="/diagrams")

@patch("gateway.main.forward_request", new_callable=AsyncMock)
def test_create_diagram_success(mock_forward_request):
    new_diagram_payload = {"name": "New Diagram", "payload": {"type": "class"}}
    mock_response_data = {
        "id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
        "name": "New Diagram",
        "owner_id": "a2c0d8e0-4f39-4b69-995a-13b8b84d2de3",
        "payload_url": "s3://mock-bucket/new_diagram.json",
        "created_at": "2024-01-02T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z"
    }
    mock_forward_request.return_value = mock_response_data

    response = client.post("/diagrams", json=new_diagram_payload)

    assert response.status_code == 201
    json_response = response.json()
    assert json_response == mock_response_data
    mock_forward_request.assert_called_once_with(method="POST", path="/diagrams", json_data=new_diagram_payload)

# TODO: Add more tests for other gateway endpoints (get by id, put, delete, auth)
# TODO: Add tests for error cases (e.g., diagram service unavailable)
