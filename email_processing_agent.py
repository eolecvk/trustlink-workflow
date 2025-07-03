import os
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

from twenty_crm_api import TwentyCRMAPI
from ms_graph_api import MSGraphClient
from google import genai
from google.genai import types

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Configuration
CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ["Mail.Read"]
TWENTY_CRM_API_BASE_URL = os.environ.get("TWENTY_CRM_API_BASE_URL")
TWENTY_CRM_API_KEY = os.environ.get("TWENTY_CRM_API_KEY_PYTHON")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_DEFAULT_MODEL")

class CRMTools:
    def __init__(self, twenty_crm_client: TwentyCRMAPI, ms_graph_client: MSGraphClient):
        self.twenty_crm_client = twenty_crm_client
        self.ms_graph_client = ms_graph_client

    def get_openai_tools_schema(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_person_by_email",
                    "description": "Retrieves an existing person's information from Twenty CRM by their exact email address. This should be the first tool called if the sender's email is known.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "description": "The email address of the person to search for."}
                        },
                        "required": ["email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_person",
                    "description": "Creates a new person record in Twenty CRM. Use this only if 'get_person_by_email' confirms the person does not exist.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string", "description": "The first name of the person."},
                            "last_name": {"type": "string", "description": "The last name of the person. Can be an empty string if unknown."},
                            "email": {"type": "string", "description": "The email address of the person."}
                        },
                        "required": ["first_name", "email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_opportunities_by_person_id",
                    "description": "Retrieves all opportunities associated with a specific person ID in Twenty CRM. Use this after identifying or creating a person.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "person_id": {"type": "string", "description": "The unique ID of the person."}
                        },
                        "required": ["person_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_opportunity",
                    "description": "Creates a new opportunity (case or project) in Twenty CRM linked to a specific person. Use this if the email indicates a brand new client request for services, and no existing, relevant opportunity is found for the person.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "A concise title for the new opportunity, ideally extracted from the email subject or main intent."},
                            "description": {"type": "string", "description": "A detailed description of the opportunity, typically the cleaned content of the email body."},
                            "person_id": {"type": "string", "description": "The unique ID of the person associated with this opportunity."}
                        },
                        "required": ["title", "description", "person_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_note_to_record",
                    "description": "Adds a detailed note to an existing record (e.g., an Opportunity or a Person) in Twenty CRM. Use this for follow-ups, updates on existing cases, or general communications related to a specific record.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "record_type": {"type": "string", "enum": ["Opportunity", "Person"], "description": "The type of CRM record to add the note to (e.g., 'Opportunity', 'Person')."},
                            "record_id": {"type": "string", "description": "The unique ID of the record (Opportunity or Person) to which the note should be added."},
                            "content": {"type": "string", "description": "The full content of the note, including relevant email details (sender, subject, body)."}
                        },
                        "required": ["record_type", "record_id", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_standalone_note",
                    "description": "Adds a note to Twenty CRM that is not directly tied to an existing Opportunity but might be linked to a Person. Use this for general inquiries, internal communications, or when no relevant opportunity can be identified but the information needs to be recorded.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "The full content of the standalone note, including relevant email details (sender, subject, body)."},
                            "person_id": {"type": "string", "description": "Optional: The unique ID of the person this note is related to, if identified."}
                        },
                        "required": ["content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mark_email_processed",
                    "description": "Call this tool at the very end of processing an email, after all CRM actions have been completed, to indicate that the email has been fully handled and can be marked as read. This function interacts with the email system, not the CRM.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_id": {"type": "string", "description": "The unique ID of the email to mark as processed/read."}
                        },
                        "required": ["email_id"]
                    }
                }
            }
        ]

    def call_tool(self, tool_name: str, **kwargs):
        logger.info(f"AI requested to call tool: {tool_name} with args: {kwargs}")
        try:
            if hasattr(self.twenty_crm_client, tool_name):
                method = getattr(self.twenty_crm_client, tool_name)
            elif hasattr(self.ms_graph_client, tool_name):
                method = getattr(self.ms_graph_client, tool_name)
            else:
                raise ValueError(f"Tool '{tool_name}' not found.")
            return method(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {"error": str(e)}

class EmailProcessingAgent:
    def __init__(self, api_key, model, twenty_crm_client, ms_graph_client):
        self.llm_client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = model
        self.crm_tools = CRMTools(twenty_crm_client, ms_graph_client)

    def process_email(self, email_data):
        email_id = email_data.get("id")
        subject = email_data.get("subject", "No Subject")
        body = email_data.get("body", {}).get("content", "")
        sender = email_data.get("sender", {}).get("emailAddress", {})
        sender_email = sender.get("address", "")

        messages = [
            {
                "role": "system",
                "content": "You are an intelligent email processing agent for a legal office CRM. Your job is to analyze incoming emails and use tools to update the CRM system appropriately."
            },
            {
                "role": "user",
                "content": f"Email from {sender_email}: {subject}\n{body}"
            }
        ]

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.crm_tools.get_openai_tools_schema(),
                tool_choice="auto"
            )

            msg = response.choices[0].message
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for call in msg.tool_calls:
                    function_name = call.function.name
                    logger.info(f"Raw tool call arguments: {call.function.arguments}")
                    try:
                        arguments = json.loads(call.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in tool call arguments: {e}")
                        # Optionally skip or handle this case
                        continue

                    result = self.crm_tools.call_tool(function_name, **arguments)

                    if "error" not in result:
                        logger.info(f"Tool '{function_name}' returned: {result}")
                        
                        messages.append({
                            "role": "function",            # must be 'function' role here
                            "name": function_name,         # name cannot be empty
                            "content": json.dumps(result)  # content must be a JSON string
                        })
                    else:
                        logger.error(f"Skipping tool response due to error: {result['error']}")
                        break  # or continue

                followup = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.crm_tools.get_openai_tools_schema(),
                    tool_choice="auto"
                )
                logger.info("Final AI response: %s", followup.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error during processing: {e}")

    def run(self):
        emails = self.crm_tools.ms_graph_client.get_unread_emails()
        for email in emails:
            self.process_email(email)

if __name__ == "__main__":
    if not all([CLIENT_ID, TWENTY_CRM_API_BASE_URL, TWENTY_CRM_API_KEY, GEMINI_API_KEY]):
        logger.error("Missing environment variables.")
        exit(1)

    twenty_crm_api = TwentyCRMAPI(TWENTY_CRM_API_BASE_URL, TWENTY_CRM_API_KEY)
    ms_graph_client = MSGraphClient(CLIENT_ID, AUTHORITY, SCOPE)

    agent = EmailProcessingAgent(
        api_key=GEMINI_API_KEY,
        model=GEMINI_MODEL,
        twenty_crm_client=twenty_crm_api,
        ms_graph_client=ms_graph_client
    )
    agent.run()
