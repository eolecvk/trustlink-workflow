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

# --- Authentication Logic ---
# Try to acquire a token silently from the cache first.
# This avoids prompting the user if a valid token already exists.
accounts = app.get_accounts()
final_result = None # Initialize a variable to hold the final authentication result

if accounts:
    print("Attempting silent token acquisition...")
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result:
        print("Silent token acquisition successful.")
        final_result = result
    else:
        print("Silent token acquisition failed, proceeding with device flow.")
        # If silent acquisition fails (e.g., token expired, revoked, or scope not granted),
        # clear the account from cache and proceed to interactive flow.
        cache.remove_account(accounts[0]) # Clear the account if silent fails
else:
    print("No accounts found in cache, initiating device flow...")

# If no token was acquired silently, initiate the device code flow.
if not final_result:
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise Exception("Failed to create device flow: No user_code returned.")

    print(f"\nGo to {flow['verification_uri']} and enter code: {flow['user_code']}")
    print(f"The device code will expire in {flow['expires_in']} seconds.")

    # Loop to acquire token by device flow, giving the user time to complete the sign-in.
    # The acquire_token_by_device_flow method will poll for you.
    start_time = time.time()
    # Set a flag to indicate if we acquired a token in the loop
    token_acquired_in_loop = False

    while time.time() - start_time < flow['expires_in']:
        print("Waiting for user to complete device login...", end="\r")
        current_poll_result = app.acquire_token_by_device_flow(flow)

        if "access_token" in current_poll_result:
            print("\nToken acquired successfully via device flow.")
            final_result = current_poll_result
            token_acquired_in_loop = True
            break
        elif "error" in current_poll_result:
            # If there's an error, print it and decide whether to continue polling.
            # "authorization_pending": user hasn't completed yet, keep polling
            # "slow_down": authentication server requested a slower polling rate
            error_code = current_poll_result.get("error")
            error_description = current_poll_result.get("error_description")

            if error_code in ["authorization_pending", "slow_down"]:
                time.sleep(flow.get("interval", 5)) # Use interval from flow or default to 5 seconds
            else:
                # Other errors indicate a definite failure, so break.
                print(f"\nError during device flow: {error_code}")
                print(f"Error description: {error_description}")
                final_result = current_poll_result # Store the error result
                break
        else:
            # Unexpected result structure, break.
            print("\nUnexpected result from acquire_token_by_device_flow.")
            print(f"Full result: {current_poll_result}")
            final_result = current_poll_result # Store the unexpected result
            break
    else:
        # This block executes if the while loop completes without a 'break'
        # meaning the flow expired or an unexpected condition occurred.
        print("\nDevice flow timed out or failed to acquire token.")
        # If we reached here, and token was not acquired in loop, final_result might still be None
        # We need to capture the last poll result if it was an error
        if not token_acquired_in_loop and "error" in current_poll_result:
             final_result = current_poll_result


# --- Post-Authentication Processing ---
if final_result and "access_token" in final_result:
    print("Authentication successful.")
    # Proceed with fetching emails
    headers = {"Authorization": f"Bearer {final_result['access_token']}"}
    endpoint = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=5"

    print(f"\nFetching emails from: {endpoint}")
    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        messages = response.json()["value"]
        if messages:
            print("\n--- Latest 5 Emails ---")
            for msg in messages:
                sender = msg['from']['emailAddress'].get('name', msg['from']['emailAddress']['address'])
                subject = msg['subject']
                print(f"From: {sender} | Subject: {subject}")
            print("-----------------------")
        else:
            print("No messages found in the inbox.")
    elif response.status_code == 401:
        print(f"Failed to fetch email: HTTP 401 Unauthorized.")
        print("This usually means the access token is invalid or expired, or permissions are insufficient.")
        print(f"Response text: {response.text}")
    elif response.status_code == 403:
        print(f"Failed to fetch email: HTTP 403 Forbidden.")
        print("This indicates insufficient permissions. Check your Azure AD app's 'Mail.Read' delegated permission and admin consent.")
        print(f"Response text: {response.text}")
    else:
        print(f"Failed to fetch email: HTTP {response.status_code}")
        print(f"Response text: {response.text}")

    # Optionally, save the token cache if a new token was acquired
    # Only save if we actually got a new token and weren't using cache initially,
    # or if the cache was updated.
    # Check if a new token was acquired from device flow OR if cache was empty before
    if token_acquired_in_loop or (not accounts and final_result and "access_token" in final_result):
        try:
            with open("msal_cache.bin", "wb") as f:
                f.write(cache.serialize().encode("utf-8"))  # ✅ convert to bytes
            print("Token cache saved.")
        except Exception as e:
            print(f"Failed to save token cache: {e}")
else:
    print("\nAuthentication failed. Could not acquire access token.")
    print(f"Final MSAL result: {final_result}") # Print the full result for debugging
    raise Exception("Authentication failed")

