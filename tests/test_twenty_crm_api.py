import pytest
from unittest.mock import patch
from twenty_crm_api import TwentyCRMAPI

@pytest.fixture
def crm_api():
    return TwentyCRMAPI("https://fake.twenty.com", "test_api_key")

@patch("twenty_crm_api.requests.request")
def test_get_person_by_email_found(mock_request, crm_api):
    # Setup
    mock_response = {
        "data": [{"id": "123", "email": "test@example.com", "firstName": "John", "lastName": "Doe"}]
    }
    mock_request.return_value.status_code = 200
    mock_request.return_value.headers = {"Content-Type": "application/json"}
    mock_request.return_value.json.return_value = mock_response
    mock_request.return_value.content = b'{"data": [...]}'

    # Test
    person = crm_api.get_person_by_email("test@example.com")

    # Assert
    assert person["id"] == "123"
    assert person["email"] == "test@example.com"

@patch("twenty_crm_api.requests.request")
def test_get_person_by_email_not_found(mock_request, crm_api):
    mock_request.return_value.status_code = 200
    mock_request.return_value.headers = {"Content-Type": "application/json"}
    mock_request.return_value.json.return_value = {"data": []}
    mock_request.return_value.content = b'{"data": []}'

    person = crm_api.get_person_by_email("missing@example.com")

    assert person is None

@patch("twenty_crm_api.requests.request")
def test_create_person(mock_request, crm_api):
    mock_request.return_value.status_code = 201
    mock_request.return_value.headers = {"Content-Type": "application/json"}
    mock_request.return_value.json.return_value = {"id": "456"}
    mock_request.return_value.content = b'{"id": "456"}'

    result = crm_api.create_person("Alice", "Smith", "alice@example.com")

    assert result["id"] == "456"

@patch("twenty_crm_api.requests.request")
def test_non_json_response_handled_gracefully(mock_request, crm_api):
    mock_request.return_value.status_code = 200
    mock_request.return_value.headers = {"Content-Type": "text/html"}
    mock_request.return_value.text = "<html>not json</html>"
    mock_request.return_value.content = b"<html>not json</html>"

    result = crm_api.get_person_by_email("nonjson@example.com")

    assert result is None  # fallback logic should return None
