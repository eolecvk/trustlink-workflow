import os
import re
from crm_review_dashboard.scripts.twenty_crm_integrator import TwentyCRM

# Initialize TwentyCRM with environment variables
TWENTY_CRM_BASE_URL = os.getenv("TWENTY_CRM_BASE_URL")
TWENTY_CRM_API_KEY = os.getenv("TWENTY_CRM_API_KEY")

if not TWENTY_CRM_BASE_URL or not TWENTY_CRM_API_KEY:
    raise ValueError("TWENTY_CRM_BASE_URL and TWENTY_CRM_API_KEY environment variables must be set.")

crm_client = TwentyCRM(TWENTY_CRM_BASE_URL, TWENTY_CRM_API_KEY)

def extract_name_from_email(email: str) -> tuple[str, str]:
    """
    Extracts first and last name from an email address.
    Assumes format 'firstname.lastname@domain.com' or 'firstname@domain.com'.
    """
    name_part = email.split('@')[0]
    parts = re.split(r'[._-]', name_part) # Split by ., _, or -

    if len(parts) >= 2:
        first_name = parts[0].capitalize()
        last_name = parts[-1].capitalize()
    elif len(parts) == 1:
        first_name = parts[0].capitalize()
        last_name = "" # No distinct last name
    else:
        first_name = ""
        last_name = ""
    return first_name, last_name

def update_crm(contact_email: str, email_subject: str, email_body: str, company_name: str = None, **kwargs):
    """
    Orchestrates the update/creation of CRM entities based on incoming email data.

    Args:
        contact_email (str): The email address of the sender.
        email_subject (str): The subject of the incoming email.
        email_body (str): The body content of the incoming email.
        company_name (str, optional): The name of the company associated with the email.
                                       If not provided, attempts to infer from email domain or creates general.
        **kwargs: Additional parameters for CRM updates like status, notes, or task description.
    """
    print(f"Processing email from: {contact_email} with subject: {email_subject}")

    # --- 1. Handle Company (if applicable) ---
    company_id = None
    if company_name:
        company = crm_client.search_company_by_name(company_name)
        if company:
            company_id = company["id"]
            print(f"Found existing company: {company_name} (ID: {company_id})")
        else:
            print(f"Company '{company_name}' not found. Creating new company...")
            created_company = crm_client.create_company({"name": company_name})
            if created_company:
                company_id = created_company["id"]
                print(f"Created new company: {company_name} (ID: {company_id})")
            else:
                print(f"Failed to create company: {company_name}")
    else:
        # Attempt to derive company name from email domain if not provided explicitly
        domain = contact_email.split('@')[-1]
        if '.' in domain:
            inferred_company_name = domain.split('.')[0].replace('-', ' ').title()
            print(f"Attempting to infer company from domain: {domain} -> {inferred_company_name}")
            company = crm_client.search_company_by_name(inferred_company_name)
            if company:
                company_id = company["id"]
                print(f"Found inferred company: {inferred_company_name} (ID: {company_id})")
            else:
                print(f"Inferred company '{inferred_company_name}' not found. Skipping company creation.")


    # --- 2. Handle Contact (Person) ---
    first_name, last_name = extract_name_from_email(contact_email)
    contact_data = {
        "email": contact_email,
        "firstName": first_name,
        "lastName": last_name,
    }
    if company_id:
        contact_data["companyId"] = company_id

    contact = crm_client.search_contact_by_email(contact_email)
    if contact:
        print(f"Found existing contact: {contact_email} (ID: {contact['id']}). Updating...")
        # Add email subject and body as a note to the contact
        existing_notes = contact.get("notes", "") or ""
        new_note_content = f"\n\n--- Email received on {os.getenv('CURRENT_DATE', 'Unknown Date')} ---\nSubject: {email_subject}\nBody:\n{email_body}"
        contact_data["notes"] = existing_notes + new_note_content.strip()

        crm_client.update_contact(contact["id"], contact_data)
        contact_id = contact["id"]
    else:
        print(f"Contact '{contact_email}' not found. Creating new contact...")
        # Initial note for a new contact
        contact_data["notes"] = f"Initial contact from email:\nSubject: {email_subject}\nBody:\n{email_body}"
        created_contact = crm_client.create_contact(contact_data)
        if created_contact:
            contact_id = created_contact["id"]
            print(f"Created new contact: {contact_email} (ID: {contact_id})")
        else:
            print(f"Failed to create contact: {contact_email}")
            return # Cannot proceed without a contact

    # --- 3. Create a Note related to the email ---
    if contact_id:
        note_content = f"Incoming Email - Subject: {email_subject}\n\n{email_body}"
        # Twenty CRM doesn't have a direct "create_note" endpoint in the provided TwentyCRM class.
        # Notes are typically associated with an entity like a person or company.
        # We've already added the email content to the contact's notes above.
        # If there was a separate 'Notes' entity in Twenty, you'd add a method to TwentyCRM
        # and call it here. For now, the email content is appended to the contact's notes.
        print(f"Email content appended to notes for contact ID: {contact_id}")

    # --- 4. Create an Opportunity (Optional, based on email content/keywords) ---
    # This is a placeholder for logic that would parse email content
    # to identify if an opportunity needs to be created or updated.
    # For now, we'll assume this might be triggered by keywords or manual review.
    # Example: if "quote" or "pricing" is in subject/body.
    # if "opportunity" in email_subject.lower() or "quote" in email_body.lower():
    #     print("Potential opportunity detected. Further logic needed to create/update.")
    #     # Example: crm_client.create_opportunity({"name": email_subject, "contactId": contact_id})

    # --- 5. Create a Task (if requested) ---
    task_desc = kwargs.get("task_desc")
    if task_desc and contact_id:
        print(f"Creating task for contact ID {contact_id}: {task_desc}")
        # Twenty CRM doesn't have a direct "create_task" endpoint in the provided TwentyCRM class.
        # You would need to add a method to `TwentyCRM` to handle task creation.
        # The data model suggests 'Tasks' are a top-level entity.
        # Example: crm_client.create_task({"description": task_desc, "relatedTo": contact_id, "dueDate": "..."})
        print("Task creation functionality is a placeholder. Implement 'create_task' in TwentyCRM if needed.")

    # --- 6. Workflow Runs/Versions/Workflows ---
    # These typically represent the automation aspect within Twenty CRM itself.
    # Our connector is *triggering* updates, not managing the CRM's internal workflows directly
    # through an external API. If Twenty CRM had an API to trigger specific workflows,
    # that would be handled here. For now, this is outside the scope of direct updates
    # from incoming emails.

    print(f"CRM update process completed for {contact_email}.")

if __name__ == "__main__":
    # This block is for testing purposes.
    # In a real scenario, this function would be called by main_workflow.py
    # after processing an incoming email.

    # Set dummy environment variables for testing if they are not set
    os.environ["TWENTY_CRM_BASE_URL"] = os.getenv("TWENTY_CRM_BASE_URL", "http://localhost:3000/api/rest")
    os.environ["TWENTY_CRM_API_KEY"] = os.getenv("TWENTY_CRM_API_KEY", "your_twenty_crm_api_key_here") # Replace with a real key for live testing

    print("\n--- Testing CRM Update Logic ---")
    test_email_subject_new = "Inquiry about new product"
    test_email_body_new = "Hi team, I saw your new product and would like to get more information and pricing."
    test_sender_email_new = "jane.doe@examplecorp.com"
    test_company_name_new = "Example Corp"

    # Simulate a new incoming email
    update_crm(
        contact_email=test_sender_email_new,
        email_subject=test_email_subject_new,
        email_body=test_email_body_new,
        company_name=test_company_name_new,
        task_desc="Follow up with Jane Doe regarding new product inquiry"
    )

    print("\n--- Testing update for existing contact ---")
    test_email_subject_existing = "Following up on my previous inquiry"
    test_email_body_existing = "Just checking in on the status of the pricing information."
    test_sender_email_existing = "jane.doe@examplecorp.com" # Same email as before

    # Simulate a follow-up email from the same sender
    update_crm(
        contact_email=test_sender_email_existing,
        email_subject=test_email_subject_existing,
        email_body=test_email_body_existing,
        company_name=test_company_name_new # Use same company name to link
    )