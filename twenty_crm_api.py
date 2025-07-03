import os
import json
import requests
from dotenv import load_dotenv
import logging

# 1. Initialize basic logging (usually done once at app startup)
#    Keep this here if this file is intended to be runnable directly for testing/scripting.
#    If it's purely a library imported by a main application, the main app should configure logging.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 2. Define the module-level logger
module_logger = logging.getLogger(__name__)


# Load environment variables. Consider adding override=True for development.
load_dotenv()

# Twenty CRM API Configuration (these will be loaded from .env if present)
TWENTY_CRM_API_BASE_URL = os.environ.get("TWENTY_CRM_API_BASE_URL")
TWENTY_CRM_API_KEY = os.environ.get("TWENTY_CRM_API_KEY_PYTHON")

class TwentyCRMAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Get a logger specifically for this class.
        self.logger = logging.getLogger(self.__class__.__name__)
        # Set its level if you want it different from the root logger (optional)
        # self.logger.setLevel(logging.DEBUG)

        if not self.base_url or not self.api_key:
            self.logger.warning("API Base URL or Key not configured. Integration tests may be skipped.")

    # Modified _make_request to handle both JSON data (for POST/PUT) and URL parameters (for GET)
    def _make_request(self, method, endpoint, json_data=None, params=None):
        # Ensure endpoint doesn't start with /, as base_url likely ends with /rest
        clean_endpoint = endpoint.lstrip('/')
        url = f"{self.base_url}/{clean_endpoint}"

        self.logger.debug(f"Making {method} request to {url} with params={params}, json_data={json_data}")

        try:
            response = requests.request(method, url, headers=self.headers, json=json_data, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

            content_type = response.headers.get("Content-Type", "")

            # Handling non-JSON/empty responses
            if "application/json" not in content_type:
                self.logger.warning(
                    f"Unexpected content type '{content_type}' from {url}. "
                    f"Response text: {response.text}"
                )
                return None

            if not response.content:
                self.logger.warning(f"JSON content expected but response body is empty from {url}.")
                return None

            return response.json()

        except requests.exceptions.HTTPError as e:
            self.logger.error(
                f"HTTP error during CRM API call to {url}: {e.response.status_code} - {e.response.text}"
            )
            raise  # Re-raise the exception

        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error during CRM API call to {url}: {e}")
            raise  # Re-raise the exception

        except requests.exceptions.Timeout as e:
            self.logger.error(f"Timeout during CRM API call to {url}: {e}")
            raise  # Re-raise the exception

        except json.JSONDecodeError as e:
            self.logger.warning(
                f"Failed to decode JSON from {url}. Error: {e}. "
                f"Response text (first 200 chars): {response.text[:200]}"
            )
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"An unexpected Requests error occurred during CRM API call to {url}: {e}")
            raise

        except Exception as e:
            self.logger.critical(f"An unhandled critical error occurred during CRM API call to {url}: {e}", exc_info=True)
            raise


    def get_person_by_email(self, email: str):
        self.logger.info(f"Searching for person with email: {email}") # Consistent logger
        try:
            # Correctly use params for GET request query parameters
            people_data = self._make_request("GET", "people", params={"email": email})

            if people_data and people_data.get("data"):
                for person in people_data["data"]:
                    if person.get("email") and person["email"].lower() == email.lower():
                        self.logger.info(f"Found person: {person.get('firstName')} {person.get('lastName')} (ID: {person.get('id')})")
                        return person
            self.logger.info(f"Person with email {email} not found.")
            return None
        except requests.exceptions.RequestException as e: # Catch specific API errors if desired here, otherwise let them propagate
            self.logger.warning(f"Error retrieving person by email {email}: {e}")
            return None # Or re-raise, depending on desired error handling
        except Exception as e: # Catch other unexpected errors
            self.logger.error(f"Unexpected error in get_person_by_email for {email}: {e}", exc_info=True)
            return None


    def create_person(self, first_name: str, last_name: str, email: str):
        self.logger.info(f"Attempting to create new person: {first_name} {last_name} ({email})") # Consistent logger
        json_data = {"firstName": first_name, "lastName": last_name, "email": email}
        return self._make_request("POST", "people", json_data=json_data)


    def get_opportunities_by_person_id(self, person_id: str):
        self.logger.info(f"Searching for opportunities for person ID: {person_id}") # Consistent logger
        try:
            # Correctly use params for GET request query parameters
            opportunities_data = self._make_request("GET", "opportunities", params={"personId": person_id})
            if opportunities_data and opportunities_data.get("data"):
                self.logger.info(f"Found {len(opportunities_data['data'])} opportunities for person ID {person_id}.")
                return opportunities_data["data"]
            self.logger.info(f"No opportunities found for person ID {person_id}.")
            return []
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error retrieving opportunities for person ID {person_id}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in get_opportunities_by_person_id for {person_id}: {e}", exc_info=True)
            return []


    def create_opportunity(self, title: str, description: str, person_id: str):
        self.logger.info(f"Attempting to create new opportunity: {title} for person ID {person_id}") # Consistent logger
        json_data = {"title": title, "description": description, "personId": person_id}
        return self._make_request("POST", "opportunities", json_data=json_data)


    def add_note_to_record(self, record_type: str, record_id: str, content: str):
        self.logger.info(f"Adding note to {record_type} ID {record_id}") # Consistent logger
        json_data = {
            "content": content,
            "recordType": record_type,
            "recordId": record_id
        }
        return self._make_request("POST", "notes", json_data=json_data)


    def add_standalone_note(self, content: str, person_id: str = None):
        self.logger.info(f"Adding standalone note {'for person ID ' + person_id if person_id else ''}") # Consistent logger
        json_data = {"content": content}
        if person_id:
            json_data["personId"] = person_id
        return self._make_request("POST", "notes", json_data=json_data)

if __name__ == "__main__":
    # Example usage if you run this file directly
    # In this block, it's appropriate to use module_logger
    
    if not TWENTY_CRM_API_BASE_URL or not TWENTY_CRM_API_KEY:
        module_logger.error("API credentials not set. Please check your .env file or environment variables.")
    else:
        crm = TwentyCRMAPI(TWENTY_CRM_API_BASE_URL, TWENTY_CRM_API_KEY)
        module_logger.info("TwentyCRMAPI instance created.")