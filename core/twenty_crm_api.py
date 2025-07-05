import os
import json
import requests
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class TwentyCRMAPI:
    def __init__(self, base_url: str, api_key: str):
        if not base_url:
            raise ValueError("Base URL must be provided for TwentyCRMAPI.")
        if not api_key:
            raise ValueError("API Key must be provided for TwentyCRMAPI.")

        self.base_url = base_url
        self.api_key = api_key
        self.logger = logger

    def _make_request(self, method: str, endpoint: str, params: dict = None,
                      data: dict = None, json_data: dict = None) -> dict:
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        self.logger.debug(f"Making {method} request to {url} with params={params}, json_data={json_data}")

        try:
            response = requests.request(method, url, headers=headers, params=params, data=data, json=json_data)
            response.raise_for_status()
            return response.json() if response.text else {}
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

            data = self._make_request("GET", endpoint, params=params)
            if not isinstance(data, dict):
                self.logger.warning("Invalid response format from CRM: Expected dict, got %s", type(data))
                return {"error": "Invalid response format from CRM"}

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
            data = self._make_request("POST", endpoint, json_data=json_data)
            return data.get("data", {}).get("createPerson")
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error creating person {email}: {e}")
            return None

    def get_opportunities_by_person_id(self, person_id: str) -> list[dict]:
        self.logger.info(f"Searching for opportunities for person ID: {person_id}")
        endpoint = "opportunities"
        filter_str = f"pointOfContactId[eq]:{person_id}"
        params = {"filter": filter_str}

        try:
            data = self._make_request("GET", endpoint, params=params)
            opportunities = data.get("data", [])
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
            data = self._make_request("POST", endpoint, json_data=json_data)
            return data.get("data", {}).get("createOpportunity")
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error creating opportunity '{name}' for person ID {person_id}: {e}")
            return None

    def update_person(self, person_id: str, first_name: str = None, last_name: str = None, email: str = None, phone: str = None) -> dict | None:
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
            data = self._make_request("PUT", endpoint, json_data=json_data)
            return data.get("data", {}).get("updatePerson")
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error updating person ID {person_id}: {e}")
            return None

    def create_note(self, title: str, body: str, person_id: str = None, company_id: str = None, opportunity_id: str = None):
        log_msg_parts = [f"Adding note with title '{title}'"]
        note_data = {
            "title": title,
            "bodyV2": {
                "markdown": body,
                "blocknote": json.dumps([
                    {
                        "id": "1",
                        "type": "paragraph",
                        "props": {
                            "textColor": "default",
                            "backgroundColor": "default",
                            "textAlignment": "left"
                        },
                        "content": [{
                            "type": "text",
                            "text": body,
                            "styles": {}
                        }]
                    }
                ])
            }
        }

        try:
            self.logger.info(f"Creating note with title: '{title}'")
            note_response = self._make_request("POST", "notes", json_data=note_data)
            note = note_response.get("data", {}).get("createNote")
            if not note:
                raise ValueError(f"Failed to create note: Invalid response format. Response: {json.dumps(note_response)}")

            note_id = note.get("id")
            if not note_id:
                raise ValueError(f"Failed to create note: No ID returned. Response: {json.dumps(note)}")

            self.logger.info(f"Note created successfully with ID: {note_id}")
            linked_records_log = []

            if person_id:
                self._make_request("POST", "noteTargets", json_data={"noteId": note_id, "personId": person_id})
                linked_records_log.append(f"person ID {person_id}")
            if company_id:
                self._make_request("POST", "noteTargets", json_data={"noteId": note_id, "companyId": company_id})
                linked_records_log.append(f"company ID {company_id}")
            if opportunity_id:
                self._make_request("POST", "noteTargets", json_data={"noteId": note_id, "opportunityId": opportunity_id})
                linked_records_log.append(f"opportunity ID {opportunity_id}")

            if linked_records_log:
                log_msg_parts.append(f"and linked to: {', '.join(linked_records_log)}")
            else:
                log_msg_parts.append("with no specific links.")

            self.logger.info(" ".join(log_msg_parts))
            return note
        except Exception as e:
            self.logger.error(f"Error creating note or note target: {e}", exc_info=True)
            raise