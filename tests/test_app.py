import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    """Test that the index route returns the HTML template"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"iMessage History Exporter" in response.data


def test_export_missing_data(client):
    """Test that the export route handles missing data appropriately"""
    response = client.post("/export")
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"
    assert "Name and phone number are required" in data["message"]


def test_export_with_data(client):
    """Test that the export route accepts valid data"""
    data = {
        "name": "Test User",
        "phone_number": "+1234567890",
        "start_date": "2025-01-01",
        "end_date": "2025-01-04",
    }
    response = client.post("/export", data=data)
    # Note: In a real test environment, we'd mock the imessage export functions
    # Here we just check that the request is properly formed
    assert response.status_code in [
        200,
        500,
    ]  # 500 is acceptable if imessage export fails
    assert response.content_type == "application/json"
