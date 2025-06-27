import os
import requests
import msal
from dotenv import load_dotenv
import time # Import time for potential retries or delays

# Load environment variables from .env file
load_dotenv()

# --- Configuration from Environment Variables ---
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# Define the scopes your application needs.
# 'offline_access' is automatically added by MSAL for refresh tokens,
# so you should not include it explicitly here.
SCOPES = ["Mail.Read"]

# REDIRECT_URI is typically not directly used in device flow,
# but it's good practice to keep it consistent with your Azure AD app registration
# if you plan to use other flows (e.g., Authorization Code Flow) later.
REDIRECT_URI = "http://localhost:8000/callback"

# --- MSAL Token Cache Setup ---
cache = msal.SerializableTokenCache()
if os.path.exists("msal_cache.bin"):
    try:
        with open("msal_cache.bin", "rb") as f:
            cache.deserialize(f.read().decode("utf-8"))
        print("Loaded token cache.")
    except Exception as e:
        print(f"Failed to load token cache: {e}")

# Create a PublicClientApplication instance.
# Public clients are typically used for desktop/mobile apps where the client secret
# cannot be securely stored. Device flow is a public client scenario.
app = msal.PublicClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    token_cache=cache
)


def authenticate_and_fetch_emails_userflow():
    """
    Handles the entire user-flow authentication process (silent or device flow)
    and fetches the latest 10 emails from the user's inbox.

    Returns:
        list: A list of email message objects if successful, otherwise an empty list.
    """
    # The MSAL app and cache are already initialized at the top level of the script.
    accounts = app.get_accounts()
    final_result = None

    if accounts:
        print("Attempting silent token acquisition...")
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result:
            print("✅ Silent token acquisition successful.")
            final_result = result
        else:
            print("Silent token acquisition failed, proceeding with device flow.")
            cache.remove_account(accounts[0]) # Clear the account if silent fails

    if not final_result:
        print("Initiating device flow for authentication...")
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            print("❌ Failed to create device flow.")
            return []

        print(f"\nGo to {flow['verification_uri']} and enter code: {flow['user_code']}")
        # The acquire_token_by_device_flow will poll and block until completion.
        final_result = app.acquire_token_by_device_flow(flow)

    if final_result and "access_token" in final_result:
        print("✅ Authentication successful. Fetching emails...")
        # Save the cache for future silent acquisitions
        try:
            with open("msal_cache.bin", "wb") as f:
                f.write(cache.serialize().encode("utf-8"))
            print("Token cache saved.")
        except Exception as e:
            print(f"Failed to save token cache: {e}")

        headers = {"Authorization": f"Bearer {final_result['access_token']}"}
        # Fetching more details including bodyPreview
        endpoint = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=10&$select=subject,from,bodyPreview,id"
        
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            return response.json().get("value", [])
        else:
            print(f"❌ Failed to fetch emails: {response.status_code} - {response.text}")
            return []
    else:
        print("\n❌ Authentication failed. Could not acquire access token.")
        print(f"Final MSAL result: {final_result}")
        return []