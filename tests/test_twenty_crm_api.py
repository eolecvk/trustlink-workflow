import sys, os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import pytest
import json
import logging
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
import requests
from core.twenty_crm_api import TwentyCRMAPI # Assuming twenty_crm_api.py is in the project root

# Configure logging for the test file itself. This is separate from the TwentyCRMAPI's internal logger.
# Pytest's caplog fixture relies on standard logging.
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s') # You can adjust level if needed
test_logger = logging.getLogger(__name__)

# Load environment variables from the .env file located at the project root
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)
    test_logger.debug(f".env file loaded from: {dotenv_path}") # Use test_logger
else:
    test_logger.error(f".env file NOT found at {dotenv_path}") # Use test_logger

# --- Fixtures and Helpers ---

@pytest.fixture
def crm_api():
    """Provides a mocked TwentyCRMAPI instance for unit tests."""
    return TwentyCRMAPI("https://fake.twenty.com", "test_api_key")

@pytest.fixture
def mock_requests_request(mocker):
    """Mocks requests.request and provides a MagicMock for response customization."""
    mock_response = MagicMock()
    # Default common mock response attributes
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {} # Default empty JSON response
    mock_response.content = b'{}'
    mock_response.text = '{}'

    mocker.patch('requests.request', return_value=mock_response)
    return mock_response

def setup_mock_json_response(mock_response, status_code, data, content_type="application/json"):
    """Helper to configure a JSON mock response."""
    mock_response.status_code = status_code
    mock_response.headers = {"Content-Type": content_type}
    mock_response.json.return_value = data
    mock_response.content = json.dumps(data).encode('utf-8')
    mock_response.text = json.dumps(data)


# --- Unit Tests (Mocked HTTP Requests) ---

## People Endpoint Tests
class TestPeopleEndpointUnit:
    """Unit tests for TwentyCRMAPI methods interacting with the /people endpoint."""

    def test_get_person_by_email_found(self, crm_api, mock_requests_request):
        """Verifies get_person_by_email returns correct person data when found."""
        mock_data = {"data": [{"id": "123", "email": "test@example.com", "firstName": "John", "lastName": "Doe"}]}
        setup_mock_json_response(mock_requests_request, 200, mock_data)

        person = crm_api.get_person_by_email("test@example.com")

        assert person is not None
        assert person["id"] == "123"
        assert person["email"] == "test@example.com"
        assert person["firstName"] == "John"
        assert person["lastName"] == "Doe"
        mock_requests_request.json.assert_called_once() # Ensure json() was called

    def test_get_person_by_email_not_found(self, crm_api, mock_requests_request):
        """Verifies get_person_by_email returns None when person is not found (empty data)."""
        setup_mock_json_response(mock_requests_request, 200, {"data": []})

        person = crm_api.get_person_by_email("missing@example.com")

        assert person is None
        mock_requests_request.json.assert_called_once() # Ensure json() was called

    def test_create_person_success(self, crm_api, mock_requests_request):
        """Verifies create_person successfully creates a person."""
        mock_response_data = {"id": "456", "email": "alice@example.com"}
        setup_mock_json_response(mock_requests_request, 201, mock_response_data)

        result = crm_api.create_person("Alice", "Smith", "alice@example.com")

        assert result is not None
        assert result["id"] == "456"
        assert result["email"] == "alice@example.com"
        mock_requests_request.json.assert_called_once() # Ensure json() was called

    def test_non_json_response_handled_gracefully(self, crm_api, mock_requests_request, caplog):
            """
            Verifies that non-JSON responses are handled gracefully, logging a warning
            and returning None or an empty dict as per client logic.
            """
            mock_requests_request.status_code = 200
            mock_requests_request.headers = {"Content-Type": "text/html"}
            mock_requests_request.text = "<html>not json</html>"
            mock_requests_request.content = b"<html>not json</html>"
            # Simulate json() method failing when parsing non-JSON content (this line is now effectively redundant
            # for *this* test case, but harmless to keep if you reuse this mock setup for other scenarios
            # where json() *would* be called but fails parsing).
            mock_requests_request.json.side_effect = json.JSONDecodeError("Expecting value", "<html>", 0)

            with caplog.at_level(logging.WARNING):
                person = crm_api.get_person_by_email("nonjson@example.com")

            assert person is None # Assuming TwentyCRMAPI returns None for unparseable responses
            assert "Unexpected content type 'text/html'" in caplog.text


    def test_get_opportunities_by_person_id_found(self, crm_api, mock_requests_request):
        mock_data = {
            "data": [
                {"id": "op1", "name": "Opportunity 1"},
                {"id": "op2", "name": "Opportunity 2"},
            ]
        }
        setup_mock_json_response(mock_requests_request, 200, mock_data)

        opportunities = crm_api.get_opportunities_by_person_id("person123")

        assert isinstance(opportunities, list)
        assert len(opportunities) == 2
        assert opportunities[0]["id"] == "op1"

    def test_get_opportunities_by_person_id_empty(self, crm_api, mock_requests_request):
        setup_mock_json_response(mock_requests_request, 200, {"data": []})

        opportunities = crm_api.get_opportunities_by_person_id("person123")

        assert opportunities == []


    def test_http_error_response_raises_exception(self, crm_api, mock_requests_request):
        """Verifies that HTTP errors (e.g., 401, 404) raise an appropriate exception."""
        mock_requests_request.status_code = 401
        mock_requests_request.headers = {'Content-Type': 'application/json'}
        mock_requests_request.json.return_value = {"error": "Unauthorized"}
        # Simulate raise_for_status() behavior
        mock_requests_request.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized for url: http://fake.twenty.com/people",
            response=mock_requests_request
        )

        with pytest.raises(requests.exceptions.HTTPError) as excinfo:
            crm_api.get_person_by_email("error@example.com")

        assert excinfo.value.response.status_code == 401
        assert "Unauthorized" in str(excinfo.value)
        mock_requests_request.raise_for_status.assert_called_once()


# --- Integration Tests (Real HTTP Requests) ---

# Configuration for integration tests
# Define these in your .env file or as environment variables for sensitive data
# TWENTY_CRM_API_BASE_URL="https://your-dev-twenty-crm.com/rest"
# TWENTY_CRM_API_KEY_PYTHON="your_actual_dev_api_key"

TEST_EMAIL_INTEGRATION = "integration_test_user@example.com" # Use an email that will either be found or return a valid "not found" JSON from your real API
TEST_API_BASE_URL = os.environ.get("TWENTY_CRM_API_BASE_URL")
TEST_API_KEY = os.environ.get("TWENTY_CRM_API_KEY_PYTHON")

# Skip integration tests if environment variables are not properly set
pytestmark = pytest.mark.skipif(
    not TEST_API_BASE_URL or not TEST_API_KEY or not TEST_API_BASE_URL.endswith('/rest'),
    reason="TWENTY_CRM_API_BASE_URL or TWENTY_CRM_API_KEY_PYTHON not set, or TWENTY_CRM_API_BASE_URL does not end with '/rest' for integration tests."
)

@pytest.fixture(scope="module")
def twenty_crm_api_integration():
    """Fixture for TwentyCRMAPI instance configured for actual integration tests."""
    # The pytestmark decorator should handle skipping, but this is a fail-safe.
    if not TEST_API_BASE_URL or not TEST_API_KEY:
        pytest.skip("Integration test environment variables not set.")
    return TwentyCRMAPI(base_url=TEST_API_BASE_URL, api_key=TEST_API_KEY)


## API Endpoint Type Verification Test
class TestApiEndpointIntegration:
    """Integration tests for verifying the Twenty CRM API endpoint behavior."""

    def test_get_person_by_email_returns_json_integration(self, twenty_crm_api_integration, caplog):
        """
        Verifies that a GET request to /people?email=<test_email> returns a valid JSON response,
        even if the person is not found. This is a crucial integration test for API configuration.
        """
        api = twenty_crm_api_integration
        email_to_test = TEST_EMAIL_INTEGRATION

        with caplog.at_level(logging.WARNING): # Capture logs to check for HTML parsing warnings
            try:
                person_data = api.get_person_by_email(email_to_test)

                # Assert that the response is either a dict (found person) or None (not found),
                # which implies successful JSON parsing by TwentyCRMAPI.
                assert isinstance(person_data, (dict, type(None))), \
                    f"Expected dict or None, but got {type(person_data)}. Likely failed JSON parsing."

                # If the API returns an HTML page, your TwentyCRMAPI's _make_request
                # should log a warning about unexpected content type.
                # We assert that this warning does NOT appear if the base URL is correct.
                # This is a key check for the "returns JSON and not HTML" requirement.
                html_warning_found = False
                for record in caplog.records:
                    if "Unexpected content type 'text/html'" in record.message:
                        html_warning_found = True
                        break
                assert not html_warning_found, \
                    "Logged a warning about unexpected HTML content. Check TWENTY_CRM_API_BASE_URL."

            except requests.exceptions.HTTPError as e:
                pytest.fail(f"API returned an HTTP error status ({e.response.status_code}) instead of JSON for email '{email_to_test}': {e}")
            except requests.exceptions.RequestException as e:
                pytest.fail(f"Network or connection error during API call for email '{email_to_test}': {e}")
            except json.JSONDecodeError as e:
                 pytest.fail(f"Failed to decode JSON response from API for email '{email_to_test}'. Response was likely not JSON: {e}")
