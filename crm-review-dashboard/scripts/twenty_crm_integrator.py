"""
Interacts with the Twenty CRM API to create or update entries
"""

import requests
import json
import os

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

    def _make_request(self, method, endpoint, data=None, params=None):
        """
        Helper method to make API requests to Twenty CRM.

        Args:
            method (str): HTTP method (e.g., "GET", "POST", "PUT").
            endpoint (str): API endpoint (e.g., "/contacts", "/companies").
            data (dict, optional): JSON payload for POST/PUT requests. Defaults to None.
            params (dict, optional): Query parameters for GET requests. Defaults to None.

        Returns:
            dict or None: JSON response from the API if successful, None otherwise.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, json=data, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            return response.json()
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

    def search_contact_by_email(self, email):
        """
        Searches for an existing contact by email.

        Args:
            email (str): The email address of the contact to search for.

        Returns:
            dict or None: The contact data if found, None otherwise.
        """
        print(f"Searching for contact with email: {email}")
        # According to Twenty CRM API, filter syntax is usually like filter[field][operator]=value
        params = {"filter[email][eq]": email}
        response_data = self._make_request("GET", "/people", params=params)
        if response_data and response_data.get("data"):
            # The API returns a list of matching records. We assume the first is the one we want.
            print(f"Found contact: {response_data['data'][0].get('email')}")
            return response_data["data"][0]
        print(f"No contact found with email: {email}")
        return None

    def create_contact(self, contact_data):
        """
        Creates a new contact in Twenty CRM.

        Args:
            contact_data (dict): A dictionary containing contact details.
                                 Expected keys: firstName, lastName, email, phone, companyId (optional).

        Returns:
            dict or None: The created contact's data if successful, None otherwise.
        """
        print(f"Attempting to create contact: {contact_data.get('email')}")
        payload = {
            "firstName": contact_data.get("firstName"),
            "lastName": contact_data.get("lastName"),
            "email": contact_data.get("email"),
            "phone": contact_data.get("phone"),
            "notes": contact_data.get("notes"),
        }
        # If companyId is provided, link the contact to the company
        if contact_data.get("companyId"):
            payload["companyId"] = contact_data["companyId"]
            
        # The API spec shows 'createdBy' as an object. For simple creation, we can omit it,
        # or set it based on the API's requirements for a "source".
        # If the API requires `createdBy` for a new record, you might add:
        # payload["createdBy"] = {"source": "API"}

        created_contact = self._make_request("POST", "/people", data=payload)
        if created_contact:
            print(f"Successfully created contact: {created_contact.get('data', {}).get('firstName')} {created_contact.get('data', {}).get('lastName')}")
            return created_contact.get("data")
        return None

    def update_contact(self, contact_id, contact_data):
        """
        Updates an existing contact in Twenty CRM.

        Args:
            contact_id (str): The UUID of the contact to update.
            contact_data (dict): A dictionary containing contact details to update.

        Returns:
            dict or None: The updated contact's data if successful, None otherwise.
        """
        print(f"Attempting to update contact ID: {contact_id}")
        payload = {
            "firstName": contact_data.get("firstName"),
            "lastName": contact_data.get("lastName"),
            "email": contact_data.get("email"),
            "phone": contact_data.get("phone"),
            "notes": contact_data.get("notes"),
        }
        # If companyId is provided, link the contact to the company
        if contact_data.get("companyId"):
            payload["companyId"] = contact_data["companyId"]

        updated_contact = self._make_request("PUT", f"/people/{contact_id}", data=payload)
        if updated_contact:
            print(f"Successfully updated contact ID: {contact_id}")
            return updated_contact.get("data")
        return None

    def search_company_by_name(self, company_name):
        """
        Searches for an existing company by name.

        Args:
            company_name (str): The name of the company to search for.

        Returns:
            dict or None: The company data if found, None otherwise.
        """
        print(f"Searching for company with name: {company_name}")
        params = {"filter[name][eq]": company_name}
        response_data = self._make_request("GET", "/companies", params=params)
        if response_data and response_data.get("data"):
            print(f"Found company: {response_data['data'][0].get('name')}")
            return response_data["data"][0]
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
            payload["domainName"] = {"primaryLinkUrl": company_data["domainName"]}

        # If the API requires `createdBy` for a new record, you might add:
        # payload["createdBy"] = {"source": "API"}

        created_company = self._make_request("POST", "/companies", data=payload)
        if created_company:
            print(f"Successfully created company: {created_company.get('data', {}).get('name')}")
            return created_company.get("data")
        return None

    def update_company(self, company_id, company_data):
        """
        Updates an existing company in Twenty CRM.

        Args:
            company_id (str): The UUID of the company to update.
            company_data (dict): A dictionary containing company details to update.

        Returns:
            dict or None: The updated company's data if successful, None otherwise.
        """
        print(f"Attempting to update company ID: {company_id}")
        payload = {
            "name": company_data.get("name"),
        }
        if company_data.get("domainName"):
            payload["domainName"] = {"primaryLinkUrl": company_data["domainName"]}

        updated_company = self._make_request("PUT", f"/companies/{company_id}", data=payload)
        if updated_company:
            print(f"Successfully updated company ID: {company_id}")
            return updated_company.get("data")
        return None

if __name__ == "__main__":
    # Example Usage:
    # Make sure to set these environment variables or replace them directly for testing
    # export TWENTY_CRM_BASE_URL="http://localhost:3000/api/rest" # Or your cloud URL
    # export TWENTY_CRM_API_KEY="your_twenty_crm_api_key_here"

    TWENTY_CRM_BASE_URL = os.getenv("TWENTY_CRM_BASE_URL")
    TWENTY_CRM_API_KEY = os.getenv("TWENTY_CRM_API_KEY")

    if not TWENTY_CRM_BASE_URL or not TWENTY_CRM_API_KEY:
        print("Please set TWENTY_CRM_BASE_URL and TWENTY_CRM_API_KEY environment variables.")
    else:
        crm = TwentyCRM(TWENTY_CRM_BASE_URL, TWENTY_CRM_API_KEY)

        # --- Demo: Create or Update a Company ---
        print("\n--- Company Management Demo ---")
        test_company_name = "Acme Corp"
        test_company_domain = "acmecorp.com"

        # Search for company
        company = crm.search_company_by_name(test_company_name)

        if company:
            print(f"Company '{test_company_name}' already exists. Updating...")
            updated_company_data = {"name": test_company_name, "domainName": "newacmecorp.com"}
            crm.update_company(company["id"], updated_company_data)
        else:
            print(f"Company '{test_company_name}' not found. Creating new company...")
            new_company_data = {"name": test_company_name, "domainName": test_company_domain}
            company = crm.create_company(new_company_data)

        # --- Demo: Create or Update a Contact ---
        print("\n--- Contact Management Demo ---")
        test_contact_email = "john.doe@example.com"
        test_contact_first_name = "John"
        test_contact_last_name = "Doe"
        test_contact_phone = "+15551234567"
        test_contact_notes = "Initial inquiry via email."

        # Search for contact
        contact = crm.search_contact_by_email(test_contact_email)

        contact_payload = {
            "firstName": test_contact_first_name,
            "lastName": test_contact_last_name,
            "email": test_contact_email,
            "phone": test_contact_phone,
            "notes": test_contact_notes,
        }

        if company:
            contact_payload["companyId"] = company["id"] # Link contact to the company

        if contact:
            print(f"Contact '{test_contact_email}' already exists. Updating...")
            # Simulate an update (e.g., adding more notes or changing phone)
            contact_payload["notes"] = "Updated notes: Client followed up after initial inquiry."
            crm.update_contact(contact["id"], contact_payload)
        else:
            print(f"Contact '{test_contact_email}' not found. Creating new contact...")
            crm.create_contact(contact_payload)