import os
import json
from pathlib import Path
from outlook_email_reader_userflow import authenticate_and_fetch_emails_userflow

# Define the path for the review queue file
REVIEW_FILE_PATH = Path("crm-review-dashboard/data/review_queue.json")
if not REVIEW_FILE_PATH.parent.exists():
    os.makedirs(REVIEW_FILE_PATH.parent, exist_ok=True)


def load_existing_review_items(filepath: Path) -> list:
    """Loads the current list of items from the review queue file."""
    if filepath.exists():
        with open(filepath, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_review_items(items: list, filepath: Path):
    """Saves the updated list of items to the review queue file."""
    with open(filepath, "w") as f:
        json.dump(items, f, indent=2)

def main():
    """
    Main orchestration function using User Flow.
    Fetches emails from the logged-in user's Outlook mailbox and adds them
    to a JSON file for the Streamlit review dashboard.
    """
    print("🚀 Starting CRM automation workflow (User Flow)...")

    print("Step 1: Authenticating user and fetching emails...")
    try:
        # This single function handles silent auth or device flow and returns emails
        emails = authenticate_and_fetch_emails_userflow()
        if not emails:
            print("No emails found or authentication failed. Exiting workflow.")
            return
    except Exception as e:
        print(f"❌ An error occurred during authentication or email fetching: {e}")
        return

    # Load items already in the queue to avoid adding duplicates
    print(f"\nStep 2: Loading existing items from {REVIEW_FILE_PATH}...")
    review_queue = load_existing_review_items(REVIEW_FILE_PATH)
    existing_ids = {item.get('id') for item in review_queue}
    print(f"Found {len(review_queue)} items already in the queue.")

    new_items_added = 0
    print(f"\nStep 3: Processing {len(emails)} fetched emails...")
    for email in emails:
        # Use the immutable email 'id' from Graph API to prevent duplicates
        email_id = email.get('id')
        if not email_id or email_id in existing_ids:
            subject = email.get("subject", "No Subject")
            print(f"  - Skipping duplicate or invalid email: '{subject}'")
            continue

        # Prepare the item for the review dashboard
        sender_address = email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown Sender')
        subject = email.get("subject", "No Subject")
        
        review_item = {
            "id": email_id, # Store the unique ID from Graph API
            "sender": sender_address,
            "email_subject": subject,
            "email_body": email.get("bodyPreview", "No Body Preview Available."),
            "status": "New",
            "note": f"Email received from {sender_address}.\nSubject: {subject}",
            "task_description": "",
            "create_task": False
        }
        review_queue.append(review_item)
        existing_ids.add(email_id)
        new_items_added += 1
        print(f"  + Added to queue: '{review_item['email_subject']}'")

    if new_items_added > 0:
        print(f"\nStep 4: Saving {new_items_added} new item(s) to the review queue file...")
        save_review_items(review_queue, REVIEW_FILE_PATH)
        print("✅ Review queue updated successfully.")
    else:
        print("\nNo new items were added to the review queue.")

    print("\nWorkflow run completed.")


if __name__ == "__main__":
    main()