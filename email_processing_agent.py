# --- Unchanged imports and setup ---
import os
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

from twenty_crm_api import TwentyCRMAPI
from ms_graph_api import MSGraphClient


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv(override=True)

CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ["Mail.Read"]
TWENTY_CRM_API_BASE_URL = os.environ.get("TWENTY_CRM_API_BASE_URL")
TWENTY_CRM_API_KEY = os.environ.get("TWENTY_CRM_API_KEY_PYTHON")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_DEFAULT_MODEL")

# --- CRMTools class (unchanged) ---

class CRMTools:
    def __init__(self, twenty_crm_client: TwentyCRMAPI, ms_graph_client: MSGraphClient):
        self.twenty_crm_client = twenty_crm_client
        self.ms_graph_client = ms_graph_client

    def get_openai_tools_schema(self):
        return [
            # [tool definitions unchanged...]
            {
                "type": "function",
                "function": {
                    "name": "get_person_by_email",
                    "description": "Retrieves a person's record from the CRM by their email address.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                                "description": "The email address of the person to retrieve."
                            }
                        },
                        "required": ["email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_person",
                    "description": "Creates a new person record in the CRM.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "first_name": {
                                "type": "string",
                                "description": "The first name of the person."
                            },
                            "last_name": {
                                "type": "string",
                                "description": "The last name of the person."
                            },
                            "email": {
                                "type": "string",
                                "description": "The email address of the person (must be unique)."
                            },
                            "phone": {
                                "type": "string",
                                "description": "The phone number of the person."
                            }
                        },
                        "required": ["email"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_person",
                    "description": "Updates an existing person record in the CRM.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "person_id": {
                                "type": "string",
                                "description": "The unique identifier of the person to update."
                            },
                            "first_name": {
                                "type": "string",
                                "description": "The updated first name of the person."
                            },
                            "last_name": {
                                "type": "string",
                                "description": "The updated last name of the person."
                            },
                            "email": {
                                "type": "string",
                                "description": "The updated email address of the person (must be unique)."
                            },
                            "phone": {
                                "type": "string",
                                "description": "The updated phone number of the person."
                            }
                        },
                        "required": ["person_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_deal",
                    "description": "Creates a new deal (opportunity) in the CRM, linking it to a person.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The name of the deal."
                            },
                            "person_id": {
                                "type": "string",
                                "description": "The unique identifier of the person associated with this deal."
                            },
                            "value": {
                                "type": "number",
                                "description": "The monetary value of the deal."
                            },
                            "status": {
                                "type": "string",
                                "description": "The current status of the deal (e.g., 'New', 'Open', 'Won', 'Lost')."
                            }
                        },
                        "required": ["name", "person_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_unread_emails",
                    "description": "Retrieves unread emails from the inbox.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mark_email_as_read",
                    "description": "Marks a specific email as read.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_id": {
                                "type": "string",
                                "description": "The unique identifier of the email to mark as read."
                            }
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

# --- Updated EmailProcessingAgent with loop ---

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
                "content": "You are an intelligent email processing agent for a legal office CRM.  "
                "Your primary goal is to manage client interactions by updating the CRM. "
                "For every incoming email, first, *always* attempt to find the sender's person record using `get_person_by_email`. "
                "If no person is found, *immediately* create a new person record using `create_person`, extracting the first name and email from the email if available."
            },
            {
                "role": "user",
                "content": f"Email from {sender_email}: {subject}\n{body}"
            }
        ]

        try:
            # Allow up to 5 consecutive tool calls in a loop
            for iteration in range(5):
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.crm_tools.get_openai_tools_schema(),
                    tool_choice="auto"
                )

                msg = response.choices[0].message

                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_outputs = []
                    for call in msg.tool_calls:
                        function_name = call.function.name
                        logger.info(f"Raw tool call arguments: {call.function.arguments}")
                        try:
                            arguments = json.loads(call.function.arguments)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON in tool call arguments: {e}")
                            # Append an error message for the LLM to process
                            tool_outputs.append({
                                "role": "function",
                                "name": function_name,
                                "content": json.dumps({"error": f"Invalid JSON arguments: {e}"})
                            })
                            continue

                        result = self.crm_tools.call_tool(function_name, **arguments)

                        if "error" not in result:
                            logger.info(f"Tool '{function_name}' returned: {result}")
                            tool_outputs.append({
                                "role": "function",
                                "name": function_name,
                                "content": json.dumps(result)
                            })
                        else:
                            logger.error(f"Tool '{function_name}' returned error: {result['error']}")
                            tool_outputs.append({
                                "role": "function",
                                "name": function_name,
                                "content": json.dumps(result)
                            })
                    messages.append(msg) # Append the message with tool_calls
                    messages.extend(tool_outputs) # Append the results of the tool calls
                else:
                    logger.info("Final AI response: %s", msg.content)
                    break # Exit loop if no tool calls are made
            else:
                logger.warning("Agent reached maximum tool call iterations (5) without a final response for email ID: %s", email_id)


        except Exception as e:
            logger.error(f"Error during processing email ID {email_id}: {e}")

    def run(self):
        emails = self.crm_tools.ms_graph_client.get_unread_emails()
        for email in emails:
            self.process_email(email)

# --- Main entry point ---

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