import os
import json
import requests
from msal import PublicClientApplication
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# --- Configuration --- #
# Microsoft Graph API (Outlook) Configuration
CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ["Mail.ReadWrite"] # Consider Mail.Read if you only need to read and mark as read

# Twenty CRM API Configuration
TWENTY_CRM_API_BASE_URL = os.environ.get("TWENTY_CRM_API_BASE_URL")
TWENTY_CRM_API_KEY = os.environ.get("TWENTY_CRM_API_KEY")

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-pro") # Using Gemini for function calling

# --- Twenty CRM API Client (Re-used, assuming it's well-implemented) --- #
# This class is assumed to handle actual HTTP requests to the Twenty CRM API
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
            return response.json()
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


# --- CRM Tool Definitions for AI (Most Compelling Decision) --- #
class CRMTools:
    def __init__(self, twenty_crm_client: TwentyCRMAPI):
        self.twenty_crm_client = twenty_crm_client

    def get_tools_schema(self):
        """
        Returns a list of tool definitions (JSON schema) that the AI can use.
        These directly map to methods in TwentyCRMAPI.
        """
        return [
            {
                "name": "get_person_by_email",
                "description": "Retrieves an existing person's information from Twenty CRM by their exact email address. This should be the first tool called if the sender's email is known.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "The email address of the person to search for."}
                    },
                    "required": ["email"],
                },
            },
            {
                "name": "create_person",
                "description": "Creates a new person record in Twenty CRM. Use this only if 'get_person_by_email' confirms the person does not exist.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "first_name": {"type": "string", "description": "The first name of the person."},
                        "last_name": {"type": "string", "description": "The last name of the person. Can be an empty string if unknown."},
                        "email": {"type": "string", "description": "The email address of the person."}
                    },
                    "required": ["first_name", "email"],
                },
            },
            {
                "name": "get_opportunities_by_person_id",
                "description": "Retrieves all opportunities associated with a specific person ID in Twenty CRM. Use this after identifying or creating a person.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "person_id": {"type": "string", "description": "The unique ID of the person."}
                    },
                    "required": ["person_id"],
                },
            },
            {
                "name": "create_opportunity",
                "description": "Creates a new opportunity (case or project) in Twenty CRM linked to a specific person. Use this if the email indicates a brand new client request for services, and no existing, relevant opportunity is found for the person.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "A concise title for the new opportunity, ideally extracted from the email subject or main intent."},
                        "description": {"type": "string", "description": "A detailed description of the opportunity, typically the cleaned content of the email body."},
                        "person_id": {"type": "string", "description": "The unique ID of the person associated with this opportunity."}
                    },
                    "required": ["title", "description", "person_id"],
                },
            },
            {
                "name": "add_note_to_record",
                "description": "Adds a detailed note to an existing record (e.g., an Opportunity or a Person) in Twenty CRM. Use this for follow-ups, updates on existing cases, or general communications related to a specific record.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "record_type": {"type": "string", "enum": ["Opportunity", "Person"], "description": "The type of CRM record to add the note to (e.g., 'Opportunity', 'Person')."},
                        "record_id": {"type": "string", "description": "The unique ID of the record (Opportunity or Person) to which the note should be added."},
                        "content": {"type": "string", "description": "The full content of the note, including relevant email details (sender, subject, body)."}
                    },
                    "required": ["record_type", "record_id", "content"],
                },
            },
            {
                "name": "add_standalone_note",
                "description": "Adds a note to Twenty CRM that is not directly tied to an existing Opportunity but might be linked to a Person. Use this for general inquiries, internal communications, or when no relevant opportunity can be identified but the information needs to be recorded.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The full content of the standalone note, including relevant email details (sender, subject, body)."},
                        "person_id": {"type": "string", "description": "Optional: The unique ID of the person this note is related to, if identified."}
                    },
                    "required": ["content"],
                },
            },
             {
                "name": "mark_email_processed",
                "description": "Call this tool at the very end of processing an email, after all CRM actions have been completed, to indicate that the email has been fully handled and can be marked as read.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string", "description": "The unique ID of the email to mark as processed/read."}
                    },
                    "required": ["email_id"],
                },
            }
        ]

    def call_tool(self, tool_name: str, **kwargs):
        """Calls the appropriate TwentyCRMAPI method based on tool_name."""
        logging.info(f"AI requested to call tool: {tool_name} with args: {kwargs}")
        try:
            method = getattr(self.twenty_crm_client, tool_name, None)
            if method:
                return method(**kwargs)
            else:
                raise ValueError(f"Tool '{tool_name}' not found.")
        except Exception as e:
            logging.error(f"Error executing tool '{tool_name}': {e}")
            return {"error": str(e)} # Return error for AI to potentially handle


# --- Microsoft Graph API Functions (Refactored for clarity) --- #
class MSGraphClient:
    def __init__(self, client_id, authority, scope):
        self.client_id = client_id
        self.authority = authority
        self.scope = scope
        self._access_token = None

    def get_access_token(self):
        if not self._access_token:
            app = PublicClientApplication(self.client_id, authority=self.authority)
            accounts = app.get_accounts()
            if accounts:
                result = app.acquire_token_silent(self.scope, account=accounts[0])
            else:
                flow = app.initiate_device_flow(scopes=self.scope)
                if "user_code" not in flow:
                    raise ValueError("Failed to initiate device flow for MS Graph.")
                logging.info(flow["message"])
                result = app.acquire_token_by_device_flow(flow)

            if "access_token" in result:
                self._access_token = result["access_token"]
                logging.info("Successfully obtained Microsoft Graph API access token.")
            else:
                raise Exception(f"Could not acquire access token for MS Graph: {result.get("error_description", "No error description")}")
        return self._access_token

    def get_unread_emails(self):
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me/mailfolders/inbox/messages?$filter=isRead eq false&$select=id,subject,body,sender",
                headers=headers
            )
            response.raise_for_status()
            return response.json()["value"]
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching unread emails from MS Graph: {e}")
            raise

    def mark_email_as_read(self, email_id: str):
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {"isRead": True}
        try:
            response = requests.patch(
                f"https://graph.microsoft.com/v1.0/me/messages/{email_id}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            logging.info(f"Email {email_id} marked as read.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to mark email {email_id} as read: {e}")
            raise

# --- Email Processing Agent (Central Logic) --- #
class EmailProcessingAgent:
    def __init__(self, openrouter_api_key, openrouter_model, twenty_crm_client, ms_graph_client):
        self.openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )
        self.crm_tools = CRMTools(twenty_crm_client)
        self.ms_graph_client = ms_graph_client

    def _call_ai_with_tools(self, messages):
        """Handles the AI interaction, including tool calling."""
        try:
            # First, send the initial message with available tools
            response = self.openai_client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                tools=self.crm_tools.get_tools_schema(),
                tool_choice="auto", # Allow the model to decide whether to call a tool
                temperature=0.7,
                max_tokens=1024, # Increased max_tokens for potentially longer tool outputs or reasoning
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # If the AI wants to call a tool
            if tool_calls:
                messages.append(response_message) # Add the AI's tool call request to the history
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    tool_output = self.crm_tools.call_tool(function_name, **function_args)
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(tool_output), # Return tool output to the AI
                        }
                    )
                # After tool execution, send the tool output back to the AI for further reasoning
                final_response = self.openai_client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024,
                )
                return final_response.choices[0].message.content # Get the final text response or a new tool call
            else:
                # If the AI didn't call a tool, it's a direct text response
                return response_message.content

        except Exception as e:
            logging.error(f"Error during AI interaction: {e}")
            return f"Error: {e}"

    def process_single_email(self, email_data):
        email_id = email_data.get("id")
        subject = email_data.get("subject", "No Subject")
        # Ensure body content is plain text; if HTML, you might need an HTML stripper
        body = email_data.get("body", {}).get("content", "").strip()
        sender_email = email_data.get("sender", {}).get("emailAddress", {}).get("address", "")
        sender_name = email_data.get("sender", {}).get("emailAddress", {}).get("name", sender_email.split("@")[0].replace(".", " ").title())


        logging.info(f"Processing email from {sender_email} (Subject: {subject})")

        # Initial prompt to the AI, setting the context for its role
        messages = [
            {
                "role": "system",
                "content": """You are an intelligent email processing agent for a legal office CRM. Your primary goal is to analyze incoming emails and use the provided tools to accurately update or create records in the Twenty CRM system.
                
                Follow these steps:
                1. Always start by trying to find the sender in the CRM using `get_person_by_email`.
                2. Based on the email content and whether a person was found/created, decide the appropriate CRM action:
                   - If it's a new client seeking legal services, `create_opportunity` (after ensuring a person exists).
                   - If it's a follow-up or update related to an ongoing case, find existing opportunities for the person using `get_opportunities_by_person_id` and then use `add_note_to_record` to add the email content to the most relevant opportunity.
                   - If it's general communication not directly tied to an opportunity, use `add_standalone_note` (linked to a person if one exists).
                   - If the email is clearly spam, an out-of-office reply, or completely irrelevant, no CRM action is needed, but you must still mark the email processed.
                3. After all necessary CRM actions are completed, you MUST call the `mark_email_processed` tool with the email ID to mark the original email as read.
                4. Be concise in your direct text responses; prefer to use tools. If you need to tell me something, make it a brief summary of actions taken or why no action was taken (e.g., "Email processed: New opportunity created and email marked as read.").
                """
            },
            {
                "role": "user",
                "content": f"""
                Analyze the following email and perform the necessary CRM actions using the provided tools.

                Email Subject: {subject}
                Sender: {sender_name} <{sender_email}>
                Email Body:
                {body}

                After determining what actions to take, ensure the email is marked as processed by calling the 'mark_email_processed' tool.
                """
            }
        ]

        try:
            # The AI will now call tools iteratively within _call_ai_with_tools
            # The final response from _call_ai_with_tools is typically a textual summary
            # or the result of the last tool call if it's the `mark_email_processed` tool.
            ai_final_comment = self._call_ai_with_tools(messages)
            logging.info(f"AI's final comment for email '{subject}': {ai_final_comment}")

            # The `mark_email_processed` tool call is designed to happen within the AI's flow.
            # We don't need a separate mark_email_as_read call here if the AI successfully calls it.
            # However, as a failsafe, you might keep it here or handle it in _call_ai_with_tools if the AI doesn't call it.
            # For this example, I've added `mark_email_processed` as a tool the AI *must* call.

        except Exception as e:
            logging.error(f"Failed to process email {email_id}: {e}")
            # In case of any failure during processing, still attempt to mark as read
            # to prevent reprocessing the same problematic email infinitely.
            try:
                self.ms_graph_client.mark_email_as_read(email_id)
            except Exception as mark_e:
                logging.error(f"Failsafe: Also failed to mark email {email_id} as read after main processing error: {mark_e}")

    def run(self):
        try:
            logging.info("Starting email processing agent.")
            unread_emails = self.ms_graph_client.get_unread_emails()

            if not unread_emails:
                logging.info("No unread emails found.")
                return

            logging.info(f"Found {len(unread_emails)} unread emails. Processing...")
            for email in unread_emails:
                self.process_single_email(email)

        except Exception as e:
            logging.critical(f"A critical error occurred in the main agent loop: {e}", exc_info=True)


# --- Main Execution --- #
if __name__ == "__main__":
    # Initialize clients
    twenty_crm_api = TwentyCRMAPI(TWENTY_CRM_API_BASE_URL, TWENTY_CRM_API_KEY)
    ms_graph_client = MSGraphClient(CLIENT_ID, AUTHORITY, SCOPE)

    # Initialize and run the agent
    agent = EmailProcessingAgent(
        openrouter_api_key=OPENROUTER_API_KEY,
        openrouter_model=OPENROUTER_MODEL,
        twenty_crm_client=twenty_crm_api,
        ms_graph_client=ms_graph_client
    )
    agent.run()