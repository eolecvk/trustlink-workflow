import os
import json
import requests
import logging
from dotenv import load_dotenv

# Configure logging for the TwentyCRMAPI class.
# This logger is intended for use within the class methods.
# Basic configuration (like setting file handlers, formatters) should ideally
# be done by the main application that imports this module,
# but a default level is set here.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Default logging level for the library

class TwentyCRMAPI:
    """
    A client for interacting with the Twenty CRM API.
    Handles HTTP requests, response parsing, and structured error logging.
    """
    def __init__(self, base_url: str, api_key: str):
        """
        Initializes the TwentyCRMAPI client.

        Args:
            base_url (str): The base URL of the Twenty CRM API (e.g., "https://your.twenty.com/rest").
            api_key (str): The API key for authentication.

        Raises:
            ValueError: If base_url or api_key are not provided.
        """
        if not base_url:
            raise ValueError("Base URL must be provided for TwentyCRMAPI.")
        if not api_key:
            raise ValueError("API Key must be provided for TwentyCRMAPI.")

        self.base_url = base_url
        self.api_key = api_key
        self.logger = logger # Use the module-level logger instance

    def _make_request(self, method: str, endpoint: str, params: dict = None,
                      data: dict = None, json_data: dict = None) -> requests.Response:
        """
        Internal helper to make HTTP requests to the CRM API.

        Handles common headers, raises `requests.exceptions.HTTPError` for bad
        responses (4xx or 5xx), and logs network/connection errors.

        Args:
            method (str): HTTP method (e.g., "GET", "POST", "PUT", "DELETE").
            endpoint (str): The API endpoint (e.g., "/people", "/opportunities").
            params (dict, optional): Dictionary of URL query parameters. Defaults to None.
            data (dict, optional): Dictionary of form-encoded data. Defaults to None.
            json_data (dict, optional): Dictionary of JSON data to send in the request body. Defaults to None.

        Returns:
            requests.Response: The response object if the request was successful.

        Raises:
            requests.exceptions.HTTPError: For HTTP status codes indicating an error (4xx or 5xx).
            requests.exceptions.RequestException: For other request-related errors (e.g., network issues, timeouts).
        """
        url = f"{self.base_url}/{endpoint}" # Ensure endpoint is correctly appended
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        self.logger.debug(f"Making {method} request to {url} with params={params}, json_data={json_data}")

        try:
            response = requests.request(method, url, headers=headers, params=params, data=data, json=json_data)
            response.raise_for_status() # Raises HTTPError for 4xx/5xx responses
            return response
        except requests.exceptions.HTTPError as e:
            # Log specific HTTP error details before re-raising
            self.logger.error(f"HTTP error during CRM API call to {url}: {e.response.status_code} - {e.response.text}")
            raise # Re-raise the HTTPError for the caller to handle
        except requests.exceptions.RequestException as e:
            # Log other request exceptions (e.g., network errors, timeouts) before re-raising
            self.logger.error(f"Network or connection error during CRM API call to {url}: {e}")
            raise # Re-raise other RequestException types

    def get_person_by_email(self, email: str):
        """
        Searches for a person in the CRM by their email address using the 'emails[containsAny]' filter.

        Args:
            email (str): The email address to search for.

        Returns:
            dict: A dictionary containing a list of found people. Returns {"people": []} if no person is found,
                  or {"error": "..."} on specific parsing/unexpected data errors.

        Raises:
            requests.exceptions.HTTPError: If the CRM API returns an HTTP error status.
            requests.exceptions.RequestException: For network or connection errors during the API call.
        """
        try:
            endpoint = "people"
            # Correct filter format for 'containsAny' operator: needs an array-like string for the value.
            # Even for a single email, it should be formatted as '[ "value1" ]'.
            filter_str = f"emails[containsAny]:[\"{email}\"]"
            
            params = {"filter": filter_str}
            self.logger.info(f"Searching for person by email '{email}' using API filter: '{filter_str}'")
            
            response = self._make_request("GET", endpoint, params=params)
            data = response.json()

            if not isinstance(data, dict):
                self.logger.warning("Invalid response format from CRM: Expected dict, got %s", type(data))
                return {"error": "Invalid response format from CRM"}

            people = data.get("data", {}).get("people", [])
            if not isinstance(people, list):
                self.logger.warning("Unexpected people data structure: 'people' is not a list.")
                return {"error": "Unexpected people data structure"}

            if not people:
                self.logger.info(f"No person found via API filter for email {email}.")
                return {"people": []}
            else:
                # Client-side verification is still a good idea, as 'containsAny' might be broader
                # than an exact match, or case sensitivity might differ.
                found_people = []
                for person in people:
                    emails_data = person.get("emails", {})
                    primary = emails_data.get("primaryEmail", "").lower()
                    additional = emails_data.get("additionalEmails", []) 

                    if primary == email.lower():
                        found_people.append(person)
                        continue 
                    
                    for add_email_obj in additional:
                        if isinstance(add_email_obj, dict) and add_email_obj.get('email', '').lower() == email.lower():
                            found_people.append(person)
                            break 

                if found_people:
                    self.logger.info(f"Found {len(found_people)} person(s) by email {email}.")
                    return {"people": found_people}
                else:
                    self.logger.info(f"API returned results for email filter, but no exact match for {email} found on client-side verification.")
                    return {"people": []}

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error searching person by email {email}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error searching person by email {email}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in get_person_by_email for {email}: {e}", exc_info=True)
            return {"error": str(e)}

    def create_person(self, first_name: str, last_name: str, email: str) -> dict | None:
        """
        Creates a new person in the CRM.

        Args:
            first_name (str): The first name of the person.
            last_name (str): The last name of the person.
            email (str): The email address of the person.

        Returns:
            dict or None: The created person's data as a dictionary if successful, otherwise None.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error status.
            requests.exceptions.RequestException: For network or connection errors.
        """
        endpoint = "people"
        json_data = {
            "firstName": first_name,
            "lastName": last_name,
            "email": email
        }
        try:
            response = self._make_request("POST", endpoint, json_data=json_data)
            # Assuming successful creation returns the new resource's data directly
            return response.json()
        except requests.exceptions.HTTPError:
            raise # Re-raise HTTP errors directly
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error creating person {email}: {e}")
            return None

    def get_opportunities_by_person_id(self, person_id: str) -> list[dict]:
        """
        Retrieves opportunities associated with a specific person.

        Args:
            person_id (str): The ID of the person.

        Returns:
            list[dict]: A list of opportunity dictionaries. Returns an empty list if none found or on error.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error status.
            requests.exceptions.RequestException: For network or connection errors.
        """
        self.logger.info(f"Searching for opportunities for person ID: {person_id}")
        endpoint = "opportunities"
        params = {"personId": person_id}
        try:
            response = self._make_request("GET", endpoint, params=params)
            data = response.json()
            if data and data.get("data"):
                self.logger.info(f"Found {len(data['data'])} opportunities for person ID {person_id}.")
                return data["data"]
            self.logger.info(f"No opportunities found for person ID {person_id}.")
            return []
        except requests.exceptions.HTTPError:
            raise # Re-raise HTTP errors directly
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error retrieving opportunities for person ID {person_id}: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON for opportunities for person ID {person_id}: {e}")
            return []


    def create_opportunity(self, title: str, description: str, person_id: str) -> dict | None:
        """
        Creates a new opportunity associated with a person.

        Args:
            title (str): The title of the opportunity.
            description (str): A description of the opportunity.
            person_id (str): The ID of the person associated with this opportunity.

        Returns:
            dict or None: The created opportunity's data as a dictionary if successful, otherwise None.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error status.
            requests.exceptions.RequestException: For network or connection errors.
        """
        self.logger.info(f"Attempting to create new opportunity: '{title}' for person ID {person_id}")
        endpoint = "opportunities"
        json_data = {"title": title, "description": description, "personId": person_id}
        try:
            response = self._make_request("POST", endpoint, json_data=json_data)
            return response.json()
        except requests.exceptions.HTTPError:
            raise # Re-raise HTTP errors directly
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error creating opportunity '{title}' for person ID {person_id}: {e}")
            return None

    def add_note_to_record(self, record_type: str, record_id: str, content: str) -> dict | None:
        """
        Adds a note linked to a specific record (e.g., person, opportunity).

        Args:
            record_type (str): The type of record (e.g., "Person", "Opportunity").
            record_id (str): The ID of the record.
            content (str): The content of the note.

        Returns:
            dict or None: The created note's data as a dictionary if successful, otherwise None.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error status.
            requests.exceptions.RequestException: For network or connection errors.
        """
        self.logger.info(f"Adding note to {record_type} ID {record_id}")
        endpoint = "notes"
        json_data = {
            "content": content,
            "recordType": record_type,
            "recordId": record_id
        }
        try:
            response = self._make_request("POST", endpoint, json_data=json_data)
            return response.json()
        except requests.exceptions.HTTPError:
            raise # Re-raise HTTP errors directly
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error adding note to {record_type} ID {record_id}: {e}")
            return None

    def add_standalone_note(self, content: str, person_id: str = None) -> dict | None:
        """
        Adds a standalone note, optionally linked to a person.

        Args:
            content (str): The content of the note.
            person_id (str, optional): The ID of the person to link the note to. Defaults to None.

        Returns:
            dict or None: The created note's data as a dictionary if successful, otherwise None.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error status.
            requests.exceptions.RequestException: For network or connection errors.
        """
        log_msg = f"Adding standalone note: '{content[:50]}...'"
        if person_id:
            log_msg += f" for person ID {person_id}"
        self.logger.info(log_msg)

        endpoint = "notes"
        json_data = {"content": content}
        if person_id:
            json_data["personId"] = person_id
        try:
            response = self._make_request("POST", endpoint, json_data=json_data)
            return response.json()
        except requests.exceptions.HTTPError:
            raise # Re-raise HTTP errors directly
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error adding standalone note: {e}")
            return None


if __name__ == "__main__":
    # This block is executed only when the script is run directly, not when imported.
    # It's suitable for testing or demonstrating the API client.

    # Configure basic logging for the script's execution
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    module_logger = logging.getLogger(__name__) # Get a logger for this specific script

    # Load environment variables from .env file
    # By default, load_dotenv looks for .env in the current directory or parent directories.
    load_dotenv()
    module_logger.info(".env file loaded.")

    # Retrieve API credentials from environment variables
    TWENTY_CRM_API_BASE_URL = os.environ.get("TWENTY_CRM_API_BASE_URL")
    TWENTY_CRM_API_KEY = os.environ.get("TWENTY_CRM_API_KEY_PYTHON")

    if not TWENTY_CRM_API_BASE_URL or not TWENTY_CRM_API_KEY:
        module_logger.error(
            "API credentials not set. Please ensure TWENTY_CRM_API_BASE_URL "
            "and TWENTY_CRM_API_KEY_PYTHON are set in your .env file or environment variables."
        )
    else:
        crm = TwentyCRMAPI(TWENTY_CRM_API_BASE_URL, TWENTY_CRM_API_KEY)
        module_logger.info("TwentyCRMAPI instance created successfully.")

        # --- Example Usage ---
        test_email = "test.user@example.com"
        test_first_name = "Test"
        test_last_name = "User"

        module_logger.info(f"\n--- Attempting to get person by email: {test_email} ---")
        try:
            people_found = crm.get_person_by_email(test_email)
            if people_found and people_found.get("people"):
                person = people_found["people"][0] # Assuming we take the first match
                module_logger.info(f"Found person: {person.get('name', {}).get('firstName')} {person.get('name', {}).get('lastName')} (ID: {person['id']})")
                person_id = person['id']

                module_logger.info(f"\n--- Attempting to get opportunities for person ID: {person_id} ---")
                opportunities = crm.get_opportunities_by_person_id(person_id)
                if opportunities:
                    for opp in opportunities:
                        module_logger.info(f"  Opportunity: {opp.get('title')} (ID: {opp.get('id')})")
                else:
                    module_logger.info(f"No opportunities found for person ID {person_id}.")

                module_logger.info(f"\n--- Attempting to add a note to person ID: {person_id} ---")
                note_content = "This is a test note added via the API client."
                added_note = crm.add_note_to_record("Person", person_id, note_content)
                if added_note:
                    module_logger.info(f"Note added successfully (ID: {added_note.get('id')}).")
                else:
                    module_logger.warning("Failed to add note to person.")

            else:
                module_logger.info(f"Person with email {test_email} not found. Attempting to create...")
                new_person = crm.create_person(test_first_name, test_last_name, test_email)
                if new_person:
                    module_logger.info(f"Successfully created new person: {new_person.get('name', {}).get('firstName')} {new_person.get('name', {}).get('lastName')} (ID: {new_person['id']})")
                    person_id = new_person['id']

                    module_logger.info(f"\n--- Attempting to create an opportunity for new person ID: {person_id} ---")
                    new_opportunity = crm.create_opportunity(
                        "New Test Opportunity",
                        "This is an opportunity created for the test user.",
                        person_id
                    )
                    if new_opportunity:
                        module_logger.info(f"Opportunity created successfully (ID: {new_opportunity.get('id')}).")
                    else:
                        module_logger.warning("Failed to create opportunity.")
                else:
                    module_logger.error(f"Failed to create person with email {test_email}.")

            module_logger.info(f"\n--- Attempting to add a standalone note ---")
            standalone_note = crm.add_standalone_note("This is a standalone note without a specific record link.")
            if standalone_note:
                module_logger.info(f"Standalone note added successfully (ID: {standalone_note.get('id')}).")
            else:
                module_logger.warning("Failed to add standalone note.")

        except requests.exceptions.HTTPError as e:
            module_logger.error(f"An HTTP error occurred: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            module_logger.error(f"A network or connection error occurred: {e}")
        except Exception as e:
            module_logger.critical(f"An unexpected error occurred: {e}", exc_info=True)