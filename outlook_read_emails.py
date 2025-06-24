import os
from dotenv import load_dotenv
import msal
import requests

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
TENANT_ID = os.getenv('TENANT_ID')

if not CLIENT_ID or not TENANT_ID:
    raise Exception("CLIENT_ID and TENANT_ID must be set in environment variables.")

AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPES = ['Mail.Read']

def get_access_token():
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and 'access_token' in result:
            return result['access_token']

    flow = app.initiate_device_flow(scopes=SCOPES)
    if 'user_code' not in flow:
        raise Exception('Failed to create device flow. Check your app registration.')

    print(flow['message'])
    result = app.acquire_token_by_device_flow(flow)
    if 'access_token' in result:
        return result['access_token']
    else:
        raise Exception('Could not acquire access token.')

def read_emails(token, top=5):
    headers = {'Authorization': f'Bearer {token}'}
    endpoint = f'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top={top}&$select=subject,from,receivedDateTime'

    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        emails = response.json().get('value', [])
        print(f"Last {top} emails:")
        for i, mail in enumerate(emails, 1):
            sender = mail.get('from', {}).get('emailAddress', {}).get('name', 'Unknown sender')
            subject = mail.get('subject', 'No subject')
            received = mail.get('receivedDateTime', 'Unknown date')
            print(f"{i}. From: {sender} | Subject: {subject} | Received: {received}")
    else:
        print("Failed to get emails:", response.status_code, response.text)

if __name__ == "__main__":
    token = get_access_token()
    read_emails(token)
