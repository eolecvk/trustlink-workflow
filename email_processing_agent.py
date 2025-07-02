import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import logging

from twenty_crm_api import TwentyCRMAPI
from ms_graph_api import MSGraphClient

# Import for Google Gemini API (using genai as per your snippet)
from google import genai
from google.genai import types

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# --- Configuration --- #
# Microsoft Graph API (Outlook) Configuration
CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ["Mail.Read"]  # ["Mail.ReadWrite"] # Consider Mail.Read if you only need to read and mark as read

# Twenty CRM API Configuration
TWENTY_CRM_API_BASE_URL = os.environ.get("TWENTY_CRM_API_BASE_URL")
TWENTY_CRM_API_KEY = os.environ.get("TWENTY_CRM_API_KEY_PYTHON")

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_DEFAULT_MODEL", "deepseek/deepseek-r1-0528:free")

# Google Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_DEFAULT_MODEL", "gemini-pro") # Or "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"

# --- CRM Tool Definitions for AI --- #
class CRMTools:
    def __init__(self, twenty_crm_client: TwentyCRMAPI, ms_graph_client):
        self.twenty_crm_client = twenty_crm_client
        self.ms_graph_client = ms_graph_client

    def get_openai_tools_schema(self):
        """
        Returns a list of tool definitions (JSON schema) that OpenAI models can use.
        These directly map to methods in TwentyCRMAPI and MSGraphClient.
        """
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
                        "required": ["email"],
                    },
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
                        "required": ["first_name", "email"],
                    },
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
                        "required": ["person_id"],
                    },
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
                        "required": ["title", "description", "person_id"],
                    },
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
                        "required": ["record_type", "record_id", "content"],
                    },
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
                        "required": ["content"],
                    },
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
                        "required": ["email_id"],
                    },
                }
            }
        ]

    def get_gemini_tools_schema(self):
        """
        Returns a list of tool definitions (types.Tool) that Gemini models can use.
        """
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_person_by_email",
                        description="Retrieves an existing person's information from Twenty CRM by their exact email address. This should be the first tool called if the sender's email is known.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "email": types.Schema(type=types.Type.STRING, description="The email address of the person to search for.")
                            },
                            required=["email"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="create_person",
                        description="Creates a new person record in Twenty CRM. Use this only if 'get_person_by_email' confirms the person does not exist.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "first_name": types.Schema(type=types.Type.STRING, description="The first name of the person."),
                                "last_name": types.Schema(type=types.Type.STRING, description="The last name of the person. Can be an empty string if unknown."),
                                "email": types.Schema(type=types.Type.STRING, description="The email address of the person.")
                            },
                            required=["first_name", "email"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_opportunities_by_person_id",
                        description="Retrieves all opportunities associated with a specific person ID in Twenty CRM. Use this after identifying or creating a person.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "person_id": types.Schema(type=types.Type.STRING, description="The unique ID of the person.")
                            },
                            required=["person_id"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="create_opportunity",
                        description="Creates a new opportunity (case or project) in Twenty CRM linked to a specific person. Use this if the email indicates a brand new client request for services, and no existing, relevant opportunity is found for the person.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "title": types.Schema(type=types.Type.STRING, description="A concise title for the new opportunity, ideally extracted from the email subject or main intent."),
                                "description": types.Schema(type=types.Type.STRING, description="A detailed description of the opportunity, typically the cleaned content of the email body."),
                                "person_id": types.Schema(type=types.Type.STRING, description="The unique ID of the person associated with this opportunity.")
                            },
                            required=["title", "description", "person_id"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="add_note_to_record",
                        description="Adds a detailed note to an existing record (e.g., an Opportunity or a Person) in Twenty CRM. Use this for follow-ups, updates on existing cases, or general communications related to a specific record.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "record_type": types.Schema(type=types.Type.STRING, enum=["Opportunity", "Person"], description="The type of CRM record to add the note to (e.g., 'Opportunity', 'Person')."),
                                "record_id": types.Schema(type=types.Type.STRING, description="The unique ID of the record (Opportunity or Person) to which the note should be added."),
                                "content": types.Schema(type=types.Type.STRING, description="The full content of the note, including relevant email details (sender, subject, body).")
                            },
                            required=["record_type", "record_id", "content"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="add_standalone_note",
                        description="Adds a note to Twenty CRM that is not directly tied to an existing Opportunity but might be linked to a Person. Use this for general inquiries, internal communications, or when no relevant opportunity can be identified but the information needs to be recorded.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "content": types.Schema(type=types.Type.STRING, description="The full content of the standalone note, including relevant email details (sender, subject, body)."),
                                "person_id": types.Schema(type=types.Type.STRING, description="Optional: The unique ID of the person this note is related to, if identified.")
                            },
                            required=["content"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="mark_email_processed",
                        description="Call this tool at the very end of processing an email, after all CRM actions have been completed, to indicate that the email has been fully handled and can be marked as read. This function interacts with the email system, not the CRM.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "email_id": types.Schema(type=types.Type.STRING, description="The unique ID of the email to mark as processed/read.")
                            },
                            required=["email_id"],
                        ),
                    ),
                ]
            )
        ]


    def call_tool(self, tool_name: str, **kwargs):
        """Calls the appropriate TwentyCRMAPI or MSGraphClient method based on tool_name."""
        logging.info(f"AI requested to call tool: {tool_name} with args: {kwargs}")
        try:
            if hasattr(self.twenty_crm_client, tool_name):
                method = getattr(self.twenty_crm_client, tool_name)
            elif hasattr(self.ms_graph_client, tool_name):
                method = getattr(self.ms_graph_client, tool_name)
            else:
                raise ValueError(f"Tool '{tool_name}' not found.")

            return method(**kwargs)
        except Exception as e:
            logging.error(f"Error executing tool '{tool_name}': {e}")
            return {"error": str(e)} # Return error for AI to potentially handle

# --- Email Processing Agent (Central Logic) --- #
class EmailProcessingAgent:
    def __init__(self, llm_provider, api_key, model, twenty_crm_client, ms_graph_client):
        self.llm_provider = llm_provider
        self.model = model
        self.crm_tools = CRMTools(twenty_crm_client, ms_graph_client)
        self.ms_graph_client = ms_graph_client
        self.max_depth = 4

        if self.llm_provider == "openai":
            self.llm_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            self.tools_schema = self.crm_tools.get_openai_tools_schema()
        elif self.llm_provider == "gemini":
            # Initialize genai.Client as per your snippet
            self.llm_client = genai.Client(api_key=api_key)
            self.tools_schema = self.crm_tools.get_gemini_tools_schema()
        else:
            raise ValueError("Unsupported LLM provider. Choose 'openai' or 'gemini'.")
    def _call_ai_with_tools(self, messages, depth=0):
        """Handles the AI interaction, including tool calling, with depth limit and caching."""
        if depth > self.max_depth:
            logging.warning(f"Max recursive depth {self.max_depth} reached. Aborting further calls.")
            return "Stopped due to exceeding maximum reasoning depth."

        conversation_history_for_llm = []
        system_instruction_content = ""

        for msg in messages:
            if msg["role"] == "system":
                system_instruction_content = msg["content"]
            elif msg["role"] == "user":
                conversation_history_for_llm.append(msg["content"])
            elif msg["role"] == "assistant":
                if self.llm_provider == "openai":
                    conversation_history_for_llm.append(msg)
                elif self.llm_provider == "gemini":
                    if "tool_calls" in msg and msg["tool_calls"]:
                        for tool_call in msg["tool_calls"]:
                            conversation_history_for_llm.append(
                                types.FunctionCall(
                                    name=tool_call["function"]["name"],
                                    args=json.loads(tool_call["function"]["arguments"])
                                )
                            )
                    elif "content" in msg and msg["content"]:
                        conversation_history_for_llm.append(msg["content"])
            elif msg["role"] == "tool":
                if self.llm_provider == "openai":
                    conversation_history_for_llm.append(msg)
                elif self.llm_provider == "gemini":
                    conversation_history_for_llm.append(
                        types.FunctionResponse(
                            name=msg["name"],
                            response=json.loads(msg["content"])
                        )
                    )

        try:
            if self.llm_provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=conversation_history_for_llm,
                    tools=self.tools_schema,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1024,
                )
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls

            elif self.llm_provider == "gemini":
                response = self.llm_client.models.generate_content(
                    model=self.model,
                    contents=conversation_history_for_llm,
                    config=types.GenerateContentConfig(
                        tools=self.tools_schema,
                        system_instruction=system_instruction_content,
                        max_output_tokens=2048
                    )
                )

                logging.info(f"Raw Gemini API response: {response}")
                response_message_content = None
                tool_calls = []

                if response.candidates:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                tool_calls.append(part.function_call)
                            elif part.text:
                                response_message_content = part.text

                if response_message_content is None and not tool_calls:
                    logging.warning(f"Gemini returned no text and no tool calls. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
                    return "No relevant response or tool call from AI."

            # Tool calls
            if tool_calls:
                if self.llm_provider == "openai":
                    messages.append(response_message)
                elif self.llm_provider == "gemini":
                    gemini_tool_calls_openai_format = []
                    for tc in tool_calls:
                        gemini_tool_calls_openai_format.append({
                            "id": "gemini_call_" + tc.name,
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.args)
                            }
                        })
                    messages.append({
                        "role": "assistant",
                        "tool_calls": gemini_tool_calls_openai_format
                    })

                for tool_call in tool_calls:
                    if self.llm_provider == "gemini":
                        if isinstance(tool_call, dict):
                            function_name = tool_call["function"]["name"]
                            function_args = json.loads(tool_call["function"]["arguments"])
                            tool_call_id = tool_call["id"]
                        else:
                            function_name = tool_call.name
                            function_args = tool_call.args or {}
                            tool_call_id = "gemini_call_" + function_name
                    else:
                        function_name = tool_call.function.name
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            logging.warning(f"Invalid JSON in tool arguments: {tool_call.function.arguments}")
                            function_args = {}
                        tool_call_id = tool_call.id

                    tool_output = self.crm_tools.call_tool(function_name, **function_args)

                    messages.append(
                        {
                            "tool_call_id": tool_call_id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(tool_output),
                        }
                    )

                return self._call_ai_with_tools(messages, depth=depth + 1)

            else:
                if self.llm_provider == "openai":
                    return response_message.content
                elif self.llm_provider == "gemini":
                    return response_message_content if response_message_content else "No text response from Gemini after processing."

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
            ai_final_comment = self._call_ai_with_tools(messages)
            logging.info(f"AI's final comment for email '{subject}': {ai_final_comment}")

        except Exception as e:
            logging.error(f"Failed to process email {email_id}: {e}")
            # In case of any failure during processing, still attempt to mark as read
            # to prevent reprocessing the same problematic email infinitely.
            try:
                self.ms_graph_client.mark_email_processed(email_id) # Call the tool directly as a failsafe
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

    # --- Choose LLM Provider ---
    # Set this to "openai" for OpenRouter or "gemini" for Google Gemini
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai") # Default to "openai"

    if LLM_PROVIDER == "openai":
        llm_api_key = OPENROUTER_API_KEY
        llm_model = OPENROUTER_MODEL
        logging.info(f"Using OpenAI/OpenRouter with model: {llm_model}")
    elif LLM_PROVIDER == "gemini":
        llm_api_key = GEMINI_API_KEY
        llm_model = GEMINI_MODEL
        logging.info(f"Using Google Gemini with model: {llm_model}")
    else:
        logging.error("Invalid LLM_PROVIDER specified in environment variables. Must be 'openai' or 'gemini'.")
        exit(1)

    # Initialize and run the agent
    agent = EmailProcessingAgent(
        llm_provider=LLM_PROVIDER,
        api_key=llm_api_key,
        model=llm_model,
        twenty_crm_client=twenty_crm_api,
        ms_graph_client=ms_graph_client
    )
    agent.run()