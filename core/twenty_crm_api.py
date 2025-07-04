import os
import json
import requests
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        self.logger = logger

    def _make_request(self, method: str, endpoint: str, params: dict = None,
                      data: dict = None, json_data: dict = None) -> requests.Response:
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        self.logger.debug(f"Making {method} request to {url} with params={params}, json_data={json_data}")

        try:
            response = requests.request(method, url, headers=headers, params=params, data=data, json=json_data)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error during CRM API call to {url}: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network or connection error during CRM API call to {url}: {e}")
            raise

    def get_person_by_email(self, email: str):
        try:
            endpoint = "people"
            filter_str = f"emails.primaryEmail[eq]:{email}"
            
            params = {"filter": filter_str}
            self.logger.info(f"Searching for person by primary email '{email}' using API filter: '{filter_str}'")

            response = self._make_request("GET", endpoint, params=params)
            data = response.json()

            if not isinstance(data, dict):
                self.logger.warning("Invalid response format from CRM: Expected dict, got %s", type(data))
                return {"error": "Invalid response format from CRM"}

            # The 'people' list is nested under 'data' in the response for GET /people
            people = data.get("data", {}).get("people", [])

            if not people:
                self.logger.info(f"No person found via API filter for primary email {email}.")
                return {"people": []}
            else:
                self.logger.info(f"Found {len(people)} person(s) by primary email '{email}' via API filter.")
                return {"people": people}

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
        Creates a new person in the CRM with the correct nested structure.

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
            "emails": {
                "primaryEmail": email,
                "additionalEmails": []
            },
            "name": {
                "firstName": first_name,
                "lastName": last_name
            }
        }
        try:
            response = self._make_request("POST", endpoint, json_data=json_data)
            return response.json().get("data", {}).get("createPerson")
        except requests.exceptions.HTTPError:
            raise
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
        # Correctly using the 'filter' query parameter as per OpenAPI spec
        # The field for linking to a person in opportunities is 'pointOfContactId'
        filter_str = f"pointOfContactId[eq]:{person_id}"
        params = {"filter": filter_str}
        try:
            response = self._make_request("GET", endpoint, params=params)
            data = response.json()
            # The response for GET /opportunities nests the list under data.opportunities
            opportunities = data.get("data", {}).get("opportunities", [])
            if opportunities:
                self.logger.info(f"Found {len(opportunities)} opportunities for person ID {person_id}.")
                return opportunities
            self.logger.info(f"No opportunities found for person ID {person_id}.")
            return []
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error retrieving opportunities for person ID {person_id}: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON for opportunities for person ID {person_id}: {e}")
            return []

    def create_opportunity(self, name: str, person_id: str, value: float = None, status: str = None) -> dict | None:
        """
        Creates a new deal (opportunity) in the CRM, linking it to a person.

        Args:
            name (str): The name of the deal.
            person_id (str): The unique identifier of the person associated with this deal.
            value (float, optional): The monetary value of the deal.
            status (str, optional): The current status of the deal (e.g., 'New', 'Open', 'Won', 'Lost').

        Returns:
            dict or None: The created deal's data as a dictionary if successful, otherwise None.
        """
        self.logger.info(f"Attempting to create new opportunity: '{name}' for person ID {person_id}")
        endpoint = "opportunities"
        json_data = {
            "name": name,
            "pointOfContactId": person_id,
        }
        if value is not None:
             json_data["amount"] = {"amountMicros": int(value * 1_000_000), "currencyCode": "USD"}
        if status is not None:
             json_data["stage"] = status

        try:
            response = self._make_request("POST", endpoint, json_data=json_data)
            return response.json().get("data", {}).get("createOpportunity")
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error creating opportunity '{name}' for person ID {person_id}: {e}")
            return None

    def update_person(self, person_id: str, first_name: str = None, last_name: str = None, email: str = None, phone: str = None) -> dict | None:
        """
        Updates an existing person record in the CRM.

        Args:
            person_id (str): The unique identifier of the person to update.
            first_name (str, optional): The updated first name of the person.
            last_name (str, optional): The updated last name of the person.
            email (str, optional): The updated email address of the person (must be unique).
            phone (str, optional): The updated phone number of the person.

        Returns:
            dict or None: The updated person's data as a dictionary if successful, otherwise None.
        """
        endpoint = f"people/{person_id}"
        json_data = {}
        if first_name is not None or last_name is not None:
            json_data["name"] = {}
            if first_name is not None:
                json_data["name"]["firstName"] = first_name
            if last_name is not None:
                json_data["name"]["lastName"] = last_name
        if email is not None:
            json_data["emails"] = {"primaryEmail": email}
        if phone is not None:
            json_data["phones"] = {"primaryPhoneNumber": phone}

        if not json_data:
            self.logger.info(f"No update data provided for person ID {person_id}.")
            return None

        try:
            response = self._make_request("PUT", endpoint, json_data=json_data)
            return response.json().get("data", {}).get("updatePerson")
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error updating person ID {person_id}: {e}")
            return None

    def create_note(self, body: str, title: str = None, person_id: str = None,
                    company_id: str = None, opportunity_id: str = None, mail_id: str = None) -> dict | None:
        """
        Creates a new note record in the CRM. A note can be a standalone record or linked to a person,
        company, opportunity, or email.

        Args:
            body (str): The main content or body of the note. This will be sent as 'blocknote' within bodyV2.
            title (str, optional): The title of the note.
            person_id (str, optional): The ID of the person to associate the note with (UUID format).
            company_id (str, optional): The ID of the company to associate the note with (UUID format).
            opportunity_id (str, optional): The ID of the opportunity to associate the note with (UUID format).
            mail_id (str, optional): The ID of the email to associate the note with (UUID format).

        Returns:
            dict or None: The created note's data as a dictionary if successful, otherwise None.

        Raises:
            requests.exceptions.HTTPError: If the API returns an HTTP error status.
            requests.exceptions.RequestException: For network or connection errors.
        """
        log_msg_parts = ["Adding note"]

        # Create the BlockNote JSON structure
        blocknote_content = [
            {
                "id": "1",
                "type": "paragraph",
                "props": {
                    "textColor": "default",
                    "backgroundColor": "default",
                    "textAlignment": "left"
                },
                "content": [
                    {
                        "type": "text",
                        "text": body,
                        "styles": {}
                    }
                ]
            }
        ]

        # Stringify the BlockNote JSON
        blocknote_json_string = json.dumps(blocknote_content)

        json_data = {
            "bodyV2": {
                "markdown": body,
                "blocknote": blocknote_json_string
            }
        }

        if title:
            json_data["title"] = title
            log_msg_parts.append(f"with title '{title}'")

        # --- CRITICAL CHANGE HERE: Use 'noteTargets' array for linking ---
        note_targets = []
        linked_records_log = []

        if person_id:
            note_targets.append({"personId": person_id})
            linked_records_log.append(f"person ID {person_id}")
        if company_id:
            note_targets.append({"companyId": company_id})
            linked_records_log.append(f"company ID {company_id}")
        if opportunity_id:
            note_targets.append({"opportunityId": opportunity_id})
            linked_records_log.append(f"opportunity ID {opportunity_id}")
        if mail_id:
            note_targets.append({"mailId": mail_id})
            linked_records_log.append(f"mail ID {mail_id}")

        if note_targets:
            json_data["noteTargets"] = note_targets
            log_msg_parts.append(f"linked to: {', '.join(linked_records_log)}")
        else:
            log_msg_parts.append("as standalone")
        # --- END CRITICAL CHANGE ---

        self.logger.info(" ".join(log_msg_parts))

        endpoint = "notes"
        try:
            response = self._make_request("POST", endpoint, json_data=json_data)
            return response.json().get("data", {}).get("createNote")
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error creating note: {e}")
            return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    module_logger = logging.getLogger(__name__)

    load_dotenv()
    module_logger.info(".env file loaded.")

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
        test_first_name = "TestFN"
        test_last_name = "TestLN"

        module_logger.info(f"\n--- Attempting to get person by email: {test_email} ---")
        try:
            people_found = crm.get_person_by_email(test_email)
            if people_found and people_found.get("people"):
                person = people_found["people"][0]
                module_logger.info(f"Found person: {person.get('name', {}).get('firstName')} {person.get('name', {}).get('lastName')} (ID: {person['id']})")
                person_id = person['id']

                module_logger.info(f"\n--- Attempting to get opportunities for person ID: {person_id} ---")
                opportunities = crm.get_opportunities_by_person_id(person_id)
                if opportunities:
                    for opp in opportunities:
                        module_logger.info(f"  Opportunity: {opp.get('name')} (ID: {opp.get('id')})")
                else:
                    module_logger.info(f"No opportunities found for person ID {person_id}.")

                module_logger.info(f"\n--- Attempting to add a note to person ID: {person_id} ---")
                note_content = "This is a test note added via the API client."
                added_note = crm.add_note_to_record("Person", person_id, note_content)
                if added_note:
                    module_logger.info(f"Note added successfully (ID: {added_note.get('id')}).")
                else:
                    module_logger.warning("Failed to add note to person.")

                module_logger.info(f"\n--- Attempting to update person ID: {person_id} ---")
                updated_person = crm.update_person(person_id, first_name="UpdatedFN", last_name="UpdatedLN")
                if updated_person:
                    module_logger.info(f"Successfully updated person: {updated_person.get('name', {}).get('firstName')} {updated_person.get('name', {}).get('lastName')}")
                else:
                    module_logger.warning(f"Failed to update person ID {person_id}.")


            else:
                module_logger.info(f"Person with email {test_email} not found. Attempting to create...")
                new_person = crm.create_person(test_first_name, test_last_name, test_email)
                if new_person:
                    module_logger.info(f"Successfully created new person: {new_person.get('name', {}).get('firstName')} {new_person.get('name', {}).get('lastName')} (ID: {new_person['id']})")
                    person_id = new_person['id']

                    module_logger.info(f"\n--- Attempting to create an opportunity for new person ID: {person_id} ---")
                    new_opportunity = crm.create_opportunity(
                        "New Test Opportunity",
                        person_id,
                        value=1000.0,
                        status="NEW"
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