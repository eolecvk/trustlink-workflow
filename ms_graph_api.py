import requests
from msal import PublicClientApplication
from dotenv import load_dotenv
import logging


# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

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

    def mark_email_processed(self, email_id: str):
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


if __name__ == "__main__":
    pass