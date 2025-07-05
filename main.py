import os
import json
import logging
import time
import random
from dotenv import load_dotenv
from openai import OpenAI
from openai import RateLimitError # Specific exception for rate limits
from openai import APIStatusError # Import the base class for clarity

from core.twenty_crm_api import TwentyCRMAPI
from core.ms_graph_api import MSGraphClient
from core.prompts import SYSTEM_PROMPT
from core.tools import CRMTools

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


class EmailProcessingAgent:

    def __init__(self, api_key, model, twenty_crm_client, ms_graph_client):
        self.llm_client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = model
        self.crm_tools = CRMTools(twenty_crm_client, ms_graph_client)

    # Helper method for making LLM calls with retries
    def _call_llm_with_retries(self, messages, tools, tool_choice, max_retries=5, initial_delay=1.0):
        """
        Calls the LLM with exponential backoff and jitter for rate limit errors.
        """
        delay = initial_delay
        last_rate_limit_error = None # Variable to store the last caught RateLimitError

        for i in range(max_retries):
            try:
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice
                )
                return response
            except RateLimitError as e:
                # This is the specific exception for 429 errors from openai-python client
                last_rate_limit_error = e # Store the current RateLimitError
                # Calculate jitter proportional to the current delay
                jitter = random.uniform(0, 0.5 * delay)
                total_sleep_time = delay + jitter
                logger.warning(f"Rate limit hit (attempt {i+1}/{max_retries}). Retrying in {total_sleep_time:.2f} seconds...")
                time.sleep(total_sleep_time)
                delay *= 2 # Exponential increase
                # Optional: Cap the maximum delay to prevent excessively long waits
                # if delay > 60: # e.g., cap at 60 seconds
                #     delay = 60
            except Exception as e:
                # Catch other general exceptions during the API call
                logger.exception(f"An unexpected error occurred during LLM call:") # Use logger.exception to print traceback
                raise # Re-raise if it's not a rate limit error

        logger.error(f"Failed to get LLM response after {max_retries} retries due to rate limits.")
        # If we reach here, it means all retries failed.
        # Re-raise the last RateLimitError encountered to preserve its details.
        if last_rate_limit_error:
            raise last_rate_limit_error
        else:
            # This case should ideally not be hit if the loop exits because of RateLimitError,
            # but as a fallback, raise a general APIStatusError with dummy values
            # or a custom exception if APIStatusError cannot be constructed without real data.
            # For simplicity, if we hit this, it means no RateLimitError was ever stored
            # (which implies a different failure mode or a logic error), so a general Exception is safer.
            raise Exception("LLM call failed after retries, no specific RateLimitError captured.")


    def process_email(self, email_data):
        email_id = email_data.get("id")
        subject = email_data.get("subject", "No Subject")
        body = email_data.get("body", {}).get("content", "")
        sender = email_data.get("sender", {}).get("emailAddress", {})
        sender_email = sender.get("address", "")

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"Email from {sender_email}: {subject}\n{body}"
            }
        ]

        try:
            # Allow up to 5 consecutive tool calls in a loop
            for iteration in range(5):
                # Use the helper function for the LLM call
                response = self._call_llm_with_retries(
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
                            logger.error(f"Invalid JSON in tool call arguments for function '{function_name}': {e}")
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
            # This will now catch the re-raised RateLimitError (which is a subclass of APIStatusError and Exception)
            # or any other unhandled exception from within the loop.
            logger.error(f"Error during processing email ID {email_id}: {e}")

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