import logging
from dotenv import load_dotenv
from core.twenty_crm_api import TwentyCRMAPI
from core.ms_graph_api import MSGraphClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv(override=True)


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
                    "name": "create_opportunity",
                    "description": "Creates a new opportunity in the CRM, linking it to a person.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The name of the deal."
                            },
                            "person_id": {
                                "type": "string",
                                "description": "The unique identifier of the person associated with this opportunity."
                            },
                            "value": {
                                "type": "number",
                                "description": "The monetary value of the opportunity."
                            },
                            "status": {
                                "type": "string",
                                "description": "The current status of the opportunity (set to New by default)"
                            }
                        },
                        "required": ["name", "person_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_opportunities_by_person_id",
                    "description": "Retrieves a list of opportunities associated with a specific person.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "person_id": {
                                "type": "string",
                                "description": "The ID of the person for whom to retrieve opportunities."
                            }
                        },
                        "required": ["person_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_note",
                    "description": "Creates a new note record in the CRM. A note can be a standalone record or linked to a person, company, opportunity, or email.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the note."
                            },
                            "body": {
                                "type": "string",
                                "description": "The main content or body of the note."
                            },
                            "person_id": {
                                "type": "string",
                                "description": "Optional: The ID of the person to associate the note with (UUID format)."
                            },
                            "company_id": {
                                "type": "string",
                                "description": "Optional: The ID of the company to associate the note with (UUID format)."
                            },
                            "opportunity_id": {
                                "type": "string",
                                "description": "Optional: The ID of the opportunity to associate the note with (UUID format)."
                            }
                        },
                        "required": ["body"]
                    }
                }
            },

            # MS GRAPH
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