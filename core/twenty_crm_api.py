import os
import json
import requests
import logging
import re
from datetime import datetime

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


    def update_opportunity(self, opportunity_id: str, stage: str) -> dict | None:
        """
        Update the stage of an existing opportunity. If stage is 'invoicePaid',
        also set the close date to the current timestamp.

        Args:
            opportunity_id (str): UUID of the opportunity to update.
            stage (str): New stage value.

        Returns:
            dict | None: Updated opportunity object or None on failure.
        """
        if not opportunity_id:
            raise ValueError("Opportunity ID is required.")
        if not stage:
            raise ValueError("Stage is required.")

        endpoint = f"opportunities/{opportunity_id}"
        json_data = {"stage": stage}

        if stage == "invoicePaid":
            json_data["closeDate"] = datetime.utcnow().isoformat() + "Z"

        try:
            self.logger.info(f"Updating opportunity {opportunity_id} stage to '{stage}'")
            data = self._make_request("PATCH", endpoint, json_data=json_data)
            return data.get("data", {}).get("updateOpportunity")
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error updating opportunity {opportunity_id} stage to '{stage}': {e}")
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

    def create_note(self, email_subject: str, email_body: str, crm_update: str = None,
                    person_id: str = None, company_id: str = None, opportunity_id: str = None):
        """
        Creates a formatted note from an email and optional CRM update, and links it to CRM records.

        Args:
            email_subject (str): Subject of the email. Used as note title (required).
            email_body (str): Raw body of the email (required).
            crm_update (str): Optional summary of CRM update to include in the note body.
            person_id (str): Optional UUID of the person to link the note to.
            company_id (str): Optional UUID of the company to link the note to.
            opportunity_id (str): Optional UUID of the opportunity to link the note to.

        Returns:
            dict: The created note object from the CRM.
        """
        def build_paragraph(text: str, bold: bool = False) -> dict:
            return {
                "id": str(abs(hash(text)))[:8],
                "type": "paragraph",
                "props": {
                    "textColor": "default",
                    "backgroundColor": "default",
                    "textAlignment": "left"
                },
                "content": [{
                    "type": "text",
                    "text": text.strip(),
                    "styles": {"bold": bold} if bold else {}
                }]
            }

        try:
            if not email_subject:
                raise ValueError("Note title (email subject) is required.")
            if not email_body:
                raise ValueError("Note body (email content) is required.")

            self.logger.info(f"Creating note for subject: '{email_subject}'")

            crm_update = crm_update.strip() if crm_update else "None"

            body = f"Original email:\n{email_body.strip()}\n\nCRM update:\n{crm_update}"

            blocknote = [
                build_paragraph("Original email:", bold=True),
                build_paragraph(email_body),
                build_paragraph("CRM update:", bold=True),
                build_paragraph(crm_update)
            ]

            note_payload = {
                "title": email_subject,
                "bodyV2": {
                    "markdown": body,
                    "blocknote": json.dumps(blocknote)
                }
            }

            # Create the note
            response = self._make_request("POST", "notes", json_data=note_payload)
            note = response.get("data", {}).get("createNote")
            if not note or "id" not in note:
                raise ValueError(f"Failed to create note: {json.dumps(response)}")

            note_id = note["id"]
            self.logger.info(f"Note created with ID: {note_id} and title: '{email_subject}'")

            # Link the note to CRM entities
            targets = {
                "personId": person_id,
                "companyId": company_id,
                "opportunityId": opportunity_id
            }
            linked = []
            for key, val in targets.items():
                if val:
                    self._make_request("POST", "noteTargets", json_data={"noteId": note_id, key: val})
                    linked.append(f"{key}={val}")

            if linked:
                self.logger.info(f"Note linked to: {', '.join(linked)}")
            else:
                self.logger.info("Note not linked to any person/company/opportunity.")

            return note

        except Exception as e:
            self.logger.error(f"Error creating note or linking it: {e}", exc_info=True)
            raise

    def create_task(self, title: str, body: str, status: str = "TODO", due_at: str = None,
                    assignee_id: str = None, person_id: str = None,
                    company_id: str = None, opportunity_id: str = None,
                    position: int = 1):
        def build_paragraph(text: str, bold: bool = False) -> dict:
            return {
                "id": str(abs(hash(text)))[:8],
                "type": "paragraph",
                "props": {
                    "textColor": "default",
                    "backgroundColor": "default",
                    "textAlignment": "left"
                },
                "content": [{
                    "type": "text",
                    "text": text.strip(),
                    "styles": {"bold": bold} if bold else {}
                }]
            }

        def extract_sections(body: str) -> tuple[str, str]:
            pattern = re.compile(r"Original Email:\s*(.*?)\s*Recommendation:\s*(.*)", re.IGNORECASE | re.DOTALL)
            match = pattern.search(body)
            if match:
                return match.group(1).strip(), match.group(2).strip()
            else:
                return "", body.strip()

        try:
            self.logger.info(f"Creating task with title: '{title}'")

            original_email, recommendation = extract_sections(body)
            blocknote = []

            if original_email:
                blocknote.extend([
                    build_paragraph("Original Email:", bold=True),
                    build_paragraph(original_email),
                ])
            if recommendation:
                blocknote.extend([
                    build_paragraph("Recommendation:", bold=True),
                    build_paragraph(recommendation),
                ])
            if not blocknote:
                blocknote.extend([
                    build_paragraph("Message:", bold=True),
                    build_paragraph(body)
                ])

            task_payload = {
                "title": title,
                "status": status,
                "position": position,
                "bodyV2": {
                    "markdown": body,
                    "blocknote": json.dumps(blocknote)
                }
            }

            if due_at:
                task_payload["dueAt"] = due_at
            else:
                # Default due date: tomorrow
                task_payload["dueAt"] = (datetime.utcnow().replace(microsecond=0).isoformat() + "Z")

            if assignee_id:
                task_payload["assigneeId"] = assignee_id

            response = self._make_request("POST", "tasks", json_data=task_payload)
            task = response.get("data", {}).get("createTask")

            if not task or "id" not in task:
                raise ValueError(f"Failed to create task: {json.dumps(response)}")

            task_id = task["id"]
            self.logger.info(f"Task created with ID: {task_id}")

            # Link to related records (via taskTargets)
            targets = {
                "personId": person_id,
                "companyId": company_id,
                "opportunityId": opportunity_id
            }
            linked = []
            for key, val in targets.items():
                if val:
                    self._make_request("POST", "taskTargets", json_data={"taskId": task_id, key: val})
                    linked.append(f"{key}={val}")

            if linked:
                self.logger.info(f"Task linked to: {', '.join(linked)}")
            else:
                self.logger.info("Task not linked to any person/company/opportunity.")

            return task

        except Exception as e:
            self.logger.error(f"Error creating task or linking it: {e}", exc_info=True)
            raise