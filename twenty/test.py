import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime

# --- Configuration ---
# Get the directory of the current script
script_dir = os.path.dirname(__file__)

# Construct the path to the .env file in the parent directory of the script
DOTENV_PATH = os.path.join(script_dir, os.pardir, ".env") 

# Load environment variables from the specified .env file
load_dotenv(dotenv_path=DOTENV_PATH)

# Retrieve Twenty CRM instance URL from environment variables
# Ensure TWENTY_CRM_BASE_URL is set in your .env file
TWENTY_CRM_BASE_URL = os.getenv("TWENTY_CRM_BASE_URL")

# Retrieve the API Key from environment variables
# Ensure TWENTY_CRM_API_KEY is set in your .env file
TWENTY_CRM_API_KEY = os.getenv("TWENTY_CRM_API_KEY_PYTHON")

# Check if required environment variables are loaded successfully
if not TWENTY_CRM_BASE_URL:
    print(f"Error: TWENTY_CRM_BASE_URL not found in {DOTENV_PATH}")
    print("Please ensure your .env file exists at the specified path and contains TWENTY_CRM_BASE_URL=https://your_twenty_crm_instance.com")
    exit(1)

if not TWENTY_CRM_API_KEY:
    print(f"Error: TWENTY_CRM_API_KEY not found in {DOTENV_PATH}")
    print("Please ensure your .env file exists at the specified path and contains TWENTY_CRM_API_KEY=your_key_here")
    exit(1)

# The name of your custom object in Twenty CRM (plural form for API path)
CUSTOM_OBJECT_NAME = "emails" 

# --- API Endpoint ---
# This will now be /rest/emails
API_ENDPOINT = f"{TWENTY_CRM_BASE_URL}/rest/{CUSTOM_OBJECT_NAME}"

# --- Data for the New Email Entity ---
# Adjust these fields and their values to match your custom 'Email' object's schema
# All fields are now converted to camelCase based on previous error patterns.
new_email_data = {
    "subject": "Inquiry about new product launch", # Changed from "Subject" to "subject"
    "body": "Hi Team, I'm interested in learning more about your latest product. Can someone provide details?", # Changed from "Body" to "body"
    "name": "John Doe <john.doe@example.com>", # Changed from "Name" to "name"
    #"creationDate": datetime.utcnow().isoformat() + "Z", # Changed from "Creation date" to "creationDate"
    "payload": { # This field was already lowercase, so it remains "payload"
        "sender_email": "john.doe@example.com",
        "recipient_email": "sales@yourcompany.com",
        "is_read_status": False,
        "original_headers": "..." 
    }
}

# Convert the 'payload' dictionary to a JSON string, as the 'payload' field is of type JSON
new_email_data["payload"] = json.dumps(new_email_data["payload"])

# --- Headers for Authentication ---
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TWENTY_CRM_API_KEY}"
}

# --- Make the API Request ---
print(f"Attempting to create a new '{CUSTOM_OBJECT_NAME}' entity...")
print(f"API Endpoint: {API_ENDPOINT}")
print(f"Payload: {json.dumps(new_email_data, indent=2)}")

try:
    response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(new_email_data))

    # --- Handle the Response ---
    if response.status_code == 201: # 201 Created is typical for successful creation
        print("\nSuccessfully created new email entity!")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    elif response.status_code == 200: # Some APIs return 200 OK for creation
        print("\nSuccessfully created new email entity (HTTP 200 OK)!")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"\nFailed to create email entity. Status Code: {response.status_code}")
        print("Response Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            print(response.text)

except requests.exceptions.RequestException as e:
    print(f"\nAn error occurred during the API request: {e}")
