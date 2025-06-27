"""
Interacts with the Twenty CRM API to create or update entries,
including Companies, People, Notes, Opportunities, and Tasks.
"""

import requests
import json
import os
from datetime import datetime, timezone

class TwentyCRM:
    def __init__(self, base_url, api_key):
        """
        Initializes the TwentyCRM API client.

        Args:
            base_url (str): The base URL for the Twenty CRM API (e.g., "https://api.twenty.com/rest/").
            api_key (str): Your Twenty CRM API key.
        """
        self.base_url = base_url.rstrip('/') # Ensure no trailing slash issues
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        print(f"TwentyCRM initialized with base URL: {self.base_url}")

    def _make_request(self, method, endpoint, data=None, params=None):
        """
        Helper method to make API requests to Twenty CRM.

        Args:
            method (str): HTTP method (e.g., "GET", "POST", "PUT", "DELETE").
            endpoint (str): API endpoint (e.g., "/contacts", "/companies", "/notes").
            data (dict, optional): JSON payload for POST/PUT requests. Defaults to None.
            params (dict, optional): Query parameters for GET requests. Defaults to None.

        Returns:
            dict or None: JSON response from the API if successful, None otherwise.
        """
        url = f"{self.base_url}{endpoint}"
        print(f"Making {method} request to {url} with params: {params} and data: {data}")
        try:
            response = requests.request(method, url, headers=self.headers, json=data, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            response_json = response.json()
            print(f"Successfully made {method} request to {endpoint}. Status: {response.status_code}")
            return response_json
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error for {method} {url}: {e.response.status_code} - {e.response.text}")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error for {method} {url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            print(f"Timeout error for {method} {url}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"An unexpected request error occurred for {method} {url}: {e}")
            return None

    # --- People (Contacts) Methods ---

    def search_contact_by_email(self, email):
        """
        Searches for an existing contact by email.

        Args:
            email (str): The email address of the contact to search for.

        Returns:
            dict or None: The contact data if found, None otherwise.
                          Returns the first match if multiple are found.
        """
        print(f"Searching for contact with email: {email}")
        # Assuming Twenty CRM's /people endpoint supports filtering by email
        params = {"filter[email][eq]": email}
        response_data = self._make_request("GET", "/people", params=params)
        if response_data and response_data.get("data"):
            # The API returns a list of matching records. We assume the first is the one we want.
            found_contact = response_data["data"][0]
            print(f"Found contact: {found_contact.get('email')} (ID: {found_contact.get('id')})")
            return found_contact
        print(f"No contact found with email: {email}")
        return None

    def create_contact(self, contact_data):
        """
        Creates a new contact (person) in Twenty CRM.

        Args:
            contact_data (dict): A dictionary containing contact details.
                                 Expected keys: firstName, lastName, email, phone (optional),
                                 companyId (optional). Notes should be added via create_note.

        Returns:
            dict or None: The created contact's data if successful, None otherwise.
        """
        print(f"Attempting to create contact: {contact_data.get('email')}")
        payload = {
            "firstName": contact_data.get("firstName"),
            "lastName": contact_data.get("lastName"),
            "email": contact_data.get("email"),
            "phone": contact_data.get("phone"),
            # 'notes' field is not typically part of direct 'create_contact' payload
            # but rather added as separate 'Note' entities linked to the contact.
        }
        # If companyId is provided, link the contact to the company
        if contact_data.get("companyId"):
            payload["companyId"] = contact_data["companyId"]

        created_contact = self._make_request("POST", "/people", data=payload)
        if created_contact:
            # Assuming the API returns the created object directly or under 'data' key
            contact_result = created_contact.get("data", created_contact)
            print(f"Successfully created contact: {contact_result.get('firstName')} {contact_result.get('lastName')} (ID: {contact_result.get('id')})")
            return contact_result
        return None

    def update_contact(self, contact_id, contact_data):
        """
        Updates an existing contact (person) in Twenty CRM.

        Args:
            contact_id (str): The UUID of the contact to update.
            contact_data (dict): A dictionary containing contact details to update.
                                 Expected keys: firstName, lastName, email, phone (optional),
                                 companyId (optional).

        Returns:
            dict or None: The updated contact's data if successful, None otherwise.
        """
        print(f"Attempting to update contact ID: {contact_id}")
        payload = {
            k: v for k, v in contact_data.items() if k in ["firstName", "lastName", "email", "phone", "companyId"]
        }
        # Do not send notes in contact update payload; notes are separate entities.

        updated_contact = self._make_request("PUT", f"/people/{contact_id}", data=payload)
        if updated_contact:
            contact_result = updated_contact.get("data", updated_contact)
            print(f"Successfully updated contact ID: {contact_result.get('id')}")
            return contact_result
        return None

    # --- Company Methods ---

    def search_company_by_name(self, company_name):
        """
        Searches for an existing company by name.

        Args:
            company_name (str): The name of the company to search for.

        Returns:
            dict or None: The company data if found, None otherwise.
                          Returns the first match if multiple are found.
        """
        print(f"Searching for company with name: {company_name}")
        # Assuming Twenty CRM's /companies endpoint supports filtering by name
        params = {"filter[name][eq]": company_name}
        response_data = self._make_request("GET", "/companies", params=params)
        if response_data and response_data.get("data"):
            found_company = response_data["data"][0]
            print(f"Found company: {found_company.get('name')} (ID: {found_company.get('id')})")
            return found_company
        print(f"No company found with name: {company_name}")
        return None

    def create_company(self, company_data):
        """
        Creates a new company in Twenty CRM.

        Args:
            company_data (dict): A dictionary containing company details.
                                 Expected keys: name, domainName (optional).

        Returns:
            dict or None: The created company's data if successful, None otherwise.
        """
        print(f"Attempting to create company: {company_data.get('name')}")
        payload = {
            "name": company_data.get("name"),
        }
        # Add optional fields if they exist and are desired
        if company_data.get("domainName"):
            # Assuming domainName is structured as a nested object based on common CRM patterns
            payload["domainName"] = company_data["domainName"] # Or {"primaryLinkUrl": company_data["domainName"]} if API needs it

        created_company = self._make_request("POST", "/companies", data=payload)
        if created_company:
            company_result = created_company.get("data", created_company)
            print(f"Successfully created company: {company_result.get('name')} (ID: {company_result.get('id')})")
            return company_result
        return None

    def update_company(self, company_id, company_data):
        """
        Updates an existing company in Twenty CRM.

        Args:
            company_id (str): The UUID of the company to update.
            company_data (dict): A dictionary containing company details to update.
                                 Expected keys: name, domainName (optional).

        Returns:
            dict or None: The updated company's data if successful, None otherwise.
        """
        print(f"Attempting to update company ID: {company_id}")
        payload = {
            k: v for k, v in company_data.items() if k in ["name", "domainName"]
        }
        updated_company = self._make_request("PUT", f"/companies/{company_id}", data=payload)
        if updated_company:
            company_result = updated_company.get("data", updated_company)
            print(f"Successfully updated company ID: {company_result.get('id')}")
            return company_result
        return None

    # --- Notes Methods ---
    # Based on the data model, Notes is a top-level entity.
    # We assume Notes can be linked to People, Companies, Opportunities, Tasks.

    def create_note(self, content: str,
                    person_id: str = None, company_id: str = None,
                    opportunity_id: str = None, task_id: str = None):
        """
        Creates a new note in Twenty CRM and links it to related entities.

        Args:
            content (str): The text content of the note.
            person_id (str, optional): The ID of the person to link the note to.
            company_id (str, optional): The ID of the company to link the note to.
            opportunity_id (str, optional): The ID of the opportunity to link the note to.
            task_id (str, optional): The ID of the task to link the note to.

        Returns:
            dict or None: The created note's data if successful, None otherwise.
        """
        print(f"Attempting to create a note. Content preview: {content[:50]}...")
        payload = {
            "content": content,
            "createdAt": datetime.now(timezone.utc).isoformat(), # Use current UTC time
            "type": "email" # Or "general", "call", etc., if Twenty CRM supports types
        }
        # Link the note to relevant entities. The exact payload structure
        # for linking might vary based on Twenty CRM's API.
        # Assuming "relatedTo" or direct IDs for associations.
        # This part might need adjustment based on Twenty CRM's actual API for notes linking.
        related_entities = []
        if person_id:
            related_entities.append({"id": person_id, "type": "Person"}) # Assuming type is needed
            payload["personId"] = person_id # More likely direct ID
        if company_id:
            related_entities.append({"id": company_id, "type": "Company"})
            payload["companyId"] = company_id
        if opportunity_id:
            related_entities.append({"id": opportunity_id, "type": "Opportunity"})
            payload["opportunityId"] = opportunity_id
        if task_id:
            related_entities.append({"id": task_id, "type": "Task"})
            payload["taskId"] = task_id

        # If Twenty CRM has a generic 'relatedTo' array, use that.
        # Otherwise, specific foreign key fields like 'personId' are more common.
        # For now, we'll assume direct ID fields based on common CRM practices.
        # If the API requires a generic 'relatedTo' array:
        # if related_entities:
        #     payload["relatedTo"] = related_entities


        created_note = self._make_request("POST", "/notes", data=payload)
        if created_note:
            note_result = created_note.get("data", created_note)
            print(f"Successfully created note (ID: {note_result.get('id')})")
            return note_result
        return None

    # --- Opportunities Methods ---
    # Data model includes Opportunities. We assume CRUD operations.

    def create_opportunity(self, opportunity_data: dict):
        """
        Creates a new opportunity in Twenty CRM.

        Args:
            opportunity_data (dict): A dictionary containing opportunity details.
                                     Expected keys: name, status (e.g., "New", "Qualified"),
                                     amount (optional), currency (optional),
                                     contactId (optional), companyId (optional),
                                     expectedCloseDate (optional, ISO format).

        Returns:
            dict or None: The created opportunity's data if successful, None otherwise.
        """
        print(f"Attempting to create opportunity: {opportunity_data.get('name')}")
        payload = {
            "name": opportunity_data.get("name"),
            "status": opportunity_data.get("status", "New"), # Default status
            "amount": opportunity_data.get("amount"),
            "currency": opportunity_data.get("currency"),
            "expectedCloseDate": opportunity_data.get("expectedCloseDate"), # ISO 8601 format
        }
        if opportunity_data.get("contactId"):
            payload["contactId"] = opportunity_data["contactId"]
        if opportunity_data.get("companyId"):
            payload["companyId"] = opportunity_data["companyId"]

        created_opportunity = self._make_request("POST", "/opportunities", data=payload)
        if created_opportunity:
            opportunity_result = created_opportunity.get("data", created_opportunity)
            print(f"Successfully created opportunity: {opportunity_result.get('name')} (ID: {opportunity_result.get('id')})")
            return opportunity_result
        return None

    def update_opportunity(self, opportunity_id: str, opportunity_data: dict):
        """
        Updates an existing opportunity in Twenty CRM.

        Args:
            opportunity_id (str): The UUID of the opportunity to update.
            opportunity_data (dict): A dictionary containing opportunity details to update.

        Returns:
            dict or None: The updated opportunity's data if successful, None otherwise.
        """
        print(f"Attempting to update opportunity ID: {opportunity_id}")
        payload = {
            k: v for k, v in opportunity_data.items() if k in ["name", "status", "amount", "currency", "expectedCloseDate", "contactId", "companyId"]
        }
        updated_opportunity = self._make_request("PUT", f"/opportunities/{opportunity_id}", data=payload)
        if updated_opportunity:
            opportunity_result = updated_opportunity.get("data", updated_opportunity)
            print(f"Successfully updated opportunity ID: {opportunity_result.get('id')}")
            return opportunity_result
        return None

    def search_opportunity(self, name: str = None, contact_id: str = None, company_id: str = None):
        """
        Searches for an existing opportunity by name or related entity.

        Args:
            name (str, optional): The name of the opportunity.
            contact_id (str, optional): ID of a related contact.
            company_id (str, optional): ID of a related company.

        Returns:
            dict or None: The opportunity data if found, None otherwise.
        """
        print(f"Searching for opportunity with name: {name}, contact_id: {contact_id}, company_id: {company_id}")
        params = {}
        if name:
            params["filter[name][eq]"] = name
        if contact_id:
            params["filter[contactId][eq]"] = contact_id
        if company_id:
            params["filter[companyId][eq]"] = company_id

        if not params:
            print("No search criteria provided for opportunity.")
            return None

        response_data = self._make_request("GET", "/opportunities", params=params)
        if response_data and response_data.get("data"):
            found_opportunity = response_data["data"][0]
            print(f"Found opportunity: {found_opportunity.get('name')} (ID: {found_opportunity.get('id')})")
            return found_opportunity
        print(f"No opportunity found with provided criteria.")
        return None


    # --- Tasks Methods ---
    # Data model includes Tasks. We assume CRUD operations.

    def create_task(self, task_data: dict):
        """
        Creates a new task in Twenty CRM.

        Args:
            task_data (dict): A dictionary containing task details.
                               Expected keys: description, status (e.g., "Open", "Completed"),
                               dueDate (optional, ISO format),
                               personId (optional), companyId (optional), opportunityId (optional).

        Returns:
            dict or None: The created task's data if successful, None otherwise.
        """
        print(f"Attempting to create task: {task_data.get('description')}")
        payload = {
            "description": task_data.get("description"),
            "status": task_data.get("status", "Open"), # Default status
            "dueDate": task_data.get("dueDate"), # ISO 8601 format
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        if task_data.get("personId"):
            payload["personId"] = task_data["personId"]
        if task_data.get("companyId"):
            payload["companyId"] = task_data["companyId"]
        if task_data.get("opportunityId"):
            payload["opportunityId"] = task_data["opportunityId"]

        created_task = self._make_request("POST", "/tasks", data=payload)
        if created_task:
            task_result = created_task.get("data", created_task)
            print(f"Successfully created task: {task_result.get('description')} (ID: {task_result.get('id')})")
            return task_result
        return None

    def update_task(self, task_id: str, task_data: dict):
        """
        Updates an existing task in Twenty CRM.

        Args:
            task_id (str): The UUID of the task to update.
            task_data (dict): A dictionary containing task details to update.

        Returns:
            dict or None: The updated task's data if successful, None otherwise.
        """
        print(f"Attempting to update task ID: {task_id}")
        payload = {
            k: v for k, v in task_data.items() if k in ["description", "status", "dueDate", "personId", "companyId", "opportunityId"]
        }
        updated_task = self._make_request("PUT", f"/tasks/{task_id}", data=payload)
        if updated_task:
            task_result = updated_task.get("data", updated_task)
            print(f"Successfully updated task ID: {task_result.get('id')}")
            return task_result
        return None

    def search_task(self, description_keyword: str = None, person_id: str = None, company_id: str = None, opportunity_id: str = None):
        """
        Searches for an existing task by description keyword or related entity.

        Args:
            description_keyword (str, optional): A keyword to search in the task description.
            person_id (str, optional): ID of a related person.
            company_id (str, optional): ID of a related company.
            opportunity_id (str, optional): ID of a related opportunity.

        Returns:
            dict or None: The task data if found, None otherwise.
        """
        print(f"Searching for task with keyword: '{description_keyword}', person_id: {person_id}, company_id: {company_id}, opportunity_id: {opportunity_id}")
        params = {}
        if description_keyword:
            params["filter[description][like]"] = f"%{description_keyword}%" # Assuming 'like' operator for partial match
        if person_id:
            params["filter[personId][eq]"] = person_id
        if company_id:
            params["filter[companyId][eq]"] = company_id
        if opportunity_id:
            params["filter[opportunityId][eq]"] = opportunity_id

        if not params:
            print("No search criteria provided for task.")
            return None

        response_data = self._make_request("GET", "/tasks", params=params)
        if response_data and response_data.get("data"):
            found_task = response_data["data"][0]
            print(f"Found task: {found_task.get('description')} (ID: {found_task.get('id')})")
            return found_task
        print(f"No task found with provided criteria.")
        return None

    # --- Workflow Runs, Workflow Versions, Workflows ---
    # These typically represent internal automation within Twenty CRM.
    # It's less common for an external connector to directly create/update these
    # via a REST API, as they define the CRM's internal processes.
    # If Twenty CRM provides API endpoints for triggering or managing these,
    # methods would be added here (e.g., 'trigger_workflow(workflow_id, data)').
    # For now, we'll assume the primary interaction is with data entities.

if __name__ == "__main__":
    # Example Usage and Testing:
    # Make sure to set these environment variables or replace them directly for testing
    # export TWENTY_CRM_BASE_URL="http://localhost:3000/api/rest" # Or your cloud URL
    # export TWENTY_CRM_API_KEY="your_twenty_crm_api_key_here" # REPLACE WITH YOUR ACTUAL KEY

    TWENTY_CRM_BASE_URL = os.getenv("TWENTY_CRM_BASE_URL")
    TWENTY_CRM_API_KEY = os.getenv("TWENTY_CRM_API_KEY")

    if not TWENTY_CRM_BASE_URL or not TWENTY_CRM_API_KEY:
        print("Please set TWENTY_CRM_BASE_URL and TWENTY_CRM_API_KEY environment variables.")
        print("For testing, temporarily setting dummy values if not found.")
        TWENTY_CRM_BASE_URL = os.getenv("TWENTY_CRM_BASE_URL", "http://localhost:3000/api/rest")
        TWENTY_CRM_API_KEY = os.getenv("TWENTY_CRM_API_KEY", "dummy_api_key_for_testing")
        print(f"Using test URL: {TWENTY_CRM_BASE_URL}, Test API Key: {TWENTY_CRM_API_KEY[:5]}...")
        if TWENTY_CRM_API_KEY == "dummy_api_key_for_testing":
            print("WARNING: Using a dummy API key. API calls will likely fail. Please set a real key for live interaction.")

    crm = TwentyCRM(TWENTY_CRM_BASE_URL, TWENTY_CRM_API_KEY)

    # --- Demo: Create or Update a Company ---
    print("\n--- Company Management Demo ---")
    test_company_name = "Global Innovations Inc."
    test_company_domain = "globalinnovations.com"
    company_id = None

    company = crm.search_company_by_name(test_company_name)
    if company:
        print(f"Company '{test_company_name}' already exists. Updating...")
        updated_company_data = {"name": test_company_name, "domainName": "newglobalinnovations.net"}
        updated_comp = crm.update_company(company["id"], updated_company_data)
        if updated_comp:
            company_id = updated_comp["id"]
    else:
        print(f"Company '{test_company_name}' not found. Creating new company...")
        new_company_data = {"name": test_company_name, "domainName": test_company_domain}
        created_comp = crm.create_company(new_company_data)
        if created_comp:
            company_id = created_comp["id"]

    # --- Demo: Create or Update a Contact (Person) ---
    print("\n--- Contact Management Demo ---")
    test_contact_email = "alice.smith@globalinnovations.com"
    test_contact_first_name = "Alice"
    test_contact_last_name = "Smith"
    test_contact_phone = "+1234567890"
    person_id = None

    contact = crm.search_contact_by_email(test_contact_email)
    contact_payload = {
        "firstName": test_contact_first_name,
        "lastName": test_contact_last_name,
        "email": test_contact_email,
        "phone": test_contact_phone,
    }
    if company_id:
        contact_payload["companyId"] = company_id

    if contact:
        print(f"Contact '{test_contact_email}' already exists. Updating...")
        # Simulate an update (e.g., changing phone)
        contact_payload["phone"] = "+1987654321"
        updated_contact = crm.update_contact(contact["id"], contact_payload)
        if updated_contact:
            person_id = updated_contact["id"]
    else:
        print(f"Contact '{test_contact_email}' not found. Creating new contact...")
        created_contact = crm.create_contact(contact_payload)
        if created_contact:
            person_id = created_contact["id"]

    # --- Demo: Create a Note ---
    print("\n--- Note Management Demo ---")
    if person_id:
        note_content = f"Initial email inquiry from Alice Smith regarding partnership. (Simulated at {datetime.now().isoformat()})"
        crm.create_note(content=note_content, person_id=person_id, company_id=company_id)
    else:
        print("Cannot create note without a person_id.")

    # --- Demo: Create an Opportunity ---
    print("\n--- Opportunity Management Demo ---")
    if person_id and company_id:
        opportunity_name = "Partnership Discussion - Global Innovations"
        # Search for existing opportunity to avoid duplicates in demo
        existing_opp = crm.search_opportunity(name=opportunity_name, contact_id=person_id)
        if not existing_opp:
            opportunity_data = {
                "name": opportunity_name,
                "status": "New Lead",
                "amount": 50000.00,
                "currency": "USD",
                "expectedCloseDate": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(), # 3 months from now
                "contactId": person_id,
                "companyId": company_id,
            }
            created_opp = crm.create_opportunity(opportunity_data)
            if created_opp:
                opportunity_id = created_opp["id"]
        else:
            opportunity_id = existing_opp["id"]
            print(f"Opportunity '{opportunity_name}' already exists (ID: {opportunity_id}).")
            # You might want to update it here instead
            crm.update_opportunity(opportunity_id, {"status": "Follow-up Sent"})
    else:
        print("Cannot create opportunity without person_id and company_id.")

    # --- Demo: Create a Task ---
    print("\n--- Task Management Demo ---")
    if person_id:
        task_description = "Follow up with Alice Smith regarding partnership discussion."
        # Check if a similar task already exists for this person
        existing_task = crm.search_task(description_keyword="Follow up with Alice Smith", person_id=person_id)
        if not existing_task:
            task_data = {
                "description": task_description,
                "status": "Open",
                "dueDate": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(), # 7 days from now
                "personId": person_id,
            }
            created_task = crm.create_task(task_data)
        else:
            print(f"Task '{task_description}' already exists for this person (ID: {existing_task['id']}).")
            # You might want to update it here instead, e.g., change status
            crm.update_task(existing_task["id"], {"status": "In Progress"})
    else:
        print("Cannot create task without a person_id.")

    print("\n--- All Demos Complete ---")