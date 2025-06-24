import os
from dotenv import load_dotenv
import requests
import msal

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_ID = os.getenv("USER_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]  # Required for client credentials flow

def get_access_token():
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY
    )

    result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" in result:
        return result["access_token"]
    else:
        print("Token acquisition failed:", result)
        raise Exception("Could not acquire token")

def read_mailboxes(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    # Read messages from a shared mailbox (you need mailbox ID or user ID)
    endpoint = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/mailFolders/inbox/messages?$top=5"

    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        emails = response.json().get("value", [])
        for i, email in enumerate(emails, 1):
            subject = email.get("subject", "No subject")
            sender = email.get("from", {}).get("emailAddress", {}).get("name", "Unknown")
            print(f"{i}. From: {sender} | Subject: {subject}")
    else:
        print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    token = get_access_token()
    read_mailboxes(token)
