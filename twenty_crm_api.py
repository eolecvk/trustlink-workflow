import os
import json
import requests
from dotenv import load_dotenv
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


load_dotenv()

# Twenty CRM API Configuration
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

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, json=data)
            response.raise_for_status()  # Raise an exception for HTTP errors
            if response.content and "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            else:
                logging.warning(f"Unexpected content type or empty response from {url}: {response.text}")
                return {}
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error during CRM API call to {url}: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error during CRM API call to {url}: {e}")
            raise
        except requests.exceptions.Timeout:
            logging.error(f"Timeout during CRM API call to {url}")
            raise
        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred during CRM API call to {url}: {e}")
            raise

    def get_person_by_email(self, email: str):
        logging.info(f"Searching for person with email: {email}")
        # Assuming Twenty CRM has an endpoint to search by email or a way to filter
        # This is a placeholder; actual implementation depends on Twenty CRM's API
        try:
            # Often, search is on a list endpoint with filters
            people = self._make_request("GET", f"people?email={email}")
            if people and people.get("data"): # Assuming 'data' key holds the list
                for person in people["data"]:
                    if person.get("email") and person["email"].lower() == email.lower():
                        logging.info(f"Found person: {person.get('firstName')} {person.get('lastName')} (ID: {person.get('id')})")
                        return person
            logging.info(f"Person with email {email} not found.")
            return None
        except Exception as e:
            logging.warning(f"Could not retrieve person by email {email}: {e}")
            return None # Return None if not found or error occurred

    def create_person(self, first_name: str, last_name: str, email: str):
        logging.info(f"Attempting to create new person: {first_name} {last_name} ({email})")
        data = {"firstName": first_name, "lastName": last_name, "email": email}
        return self._make_request("POST", "people", data=data)

    def get_opportunities_by_person_id(self, person_id: str):
        logging.info(f"Searching for opportunities for person ID: {person_id}")
        # Assuming an endpoint like /people/{person_id}/opportunities or /opportunities?personId={person_id}
        try:
            opportunities = self._make_request("GET", f"opportunities?personId={person_id}")
            if opportunities and opportunities.get("data"):
                logging.info(f"Found {len(opportunities['data'])} opportunities for person ID {person_id}.")
                return opportunities["data"]
            logging.info(f"No opportunities found for person ID {person_id}.")
            return []
        except Exception as e:
            logging.warning(f"Could not retrieve opportunities for person ID {person_id}: {e}")
            return []

    def create_opportunity(self, title: str, description: str, person_id: str):
        logging.info(f"Attempting to create new opportunity: {title} for person ID {person_id}")
        data = {"title": title, "description": description, "personId": person_id}
        return self._make_request("POST", "opportunities", data=data)

    def add_note_to_record(self, record_type: str, record_id: str, content: str):
        logging.info(f"Adding note to {record_type} ID {record_id}")
        # This assumes a generic note endpoint or specific ones for each record type
        # For simplicity, let's assume a generic notes endpoint
        data = {
            "content": content,
            "recordType": record_type, # e.g., "Opportunity", "Person"
            "recordId": record_id
        }
        return self._make_request("POST", "notes", data=data)

    def add_standalone_note(self, content: str, person_id: str = None):
        logging.info(f"Adding standalone note {'for person ID ' + person_id if person_id else ''}")
        data = {"content": content}
        if person_id:
            # Assuming a way to link standalone notes to a person
            data["personId"] = person_id
        return self._make_request("POST", "notes", data=data)
    
if __name__ == "__main__":
    pass