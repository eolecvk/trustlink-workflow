import os
from dotenv import load_dotenv
from pathlib import Path
import requests
import msal

# Load .env file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# You can list one or more user IDs here (email or object ID)
USER_IDS = os.getenv("USER_IDS", "").split(",")

print(f"CLIENT_ID: {CLIENT_ID}")
print(f"CLIENT_SECRET: {CLIENT_SECRET[:4]}...")  # partial print
print(f"TENANT_ID: {TENANT_ID}")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]


def get_access_token():
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY,
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in result:
        return result["access_token"]
    else:
        print("Token acquisition failed:", result)
        raise Exception("Could not acquire token")


def read_mailbox(user_id, access_token):
    print(f"\n📬 Checking mailbox for: {user_id}")
    headers = {"Authorization": f"Bearer {access_token}"}
    endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/inbox/messages?$top=5"

    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        emails = response.json().get("value", [])
        if not emails:
            print("Inbox is empty.")
        for i, email in enumerate(emails, 1):
            subject = email.get("subject", "No subject")
            sender = email.get("from", {}).get("emailAddress", {}).get("name", "Unknown")
            print(f"{i}. From: {sender} | Subject: {subject}")
    else:
        print(f"❌ Error for {user_id} - {response.status_code}: {response.text}")


if __name__ == "__main__":
    if not USER_IDS or USER_IDS == [""]:
        raise ValueError("USER_IDS is not defined in .env")

    token = get_access_token()
    for uid in USER_IDS:
        read_mailbox(uid.strip(), token)
