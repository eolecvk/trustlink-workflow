import streamlit as st
import json
from datetime import datetime
import logging
import os # For checking if data directory exists

# --- Configuration and Setup ---

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure the data directory exists
DATA_DIR = "crm-review-dashboard/data"
REVIEW_FILE = os.path.join(DATA_DIR, "review_queue.json")
ARCHIVE_FILE = os.path.join(DATA_DIR, "reviewed_archive.json")

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logging.info(f"Created data directory: {DATA_DIR}")

# --- CRM Integration (Simulated for demonstration) ---
# You'll replace this with your actual CRM integration
try:
    from crm.push_update import update_crm
    logging.info("Successfully imported crm.push_update.update_crm")
except ImportError:
    logging.warning("Could not import crm.push_update. Simulating CRM updates.")

    # Placeholder for update_crm if the actual module isn't found
    def update_crm(contact_email, status, note, task_desc=None):
        st.write(f"**SIMULATED CRM PUSH:**")
        st.write(f"  Contact: {contact_email}")
        st.write(f"  Status: {status}")
        st.write(f"  Note: {note}")
        st.write(f"  Task Desc: {task_desc}")
        # Simulate success or failure for demonstration
        if "fail" in status.lower():
            raise ValueError("Simulated CRM push failure due to 'fail' in status.")
        logging.info(f"Simulated push to CRM for {contact_email}")
        # time.sleep(1) # Simulate network delay if needed

# --- File Operations ---

def load_items(filepath):
    """Loads items from a JSON file."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"{filepath} not found. Returning empty list.")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {filepath}. File might be corrupted.")
        st.error(f"Error loading data from {filepath}. The file might be corrupted. Check logs.")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred loading {filepath}: {e}")
        st.error(f"An unexpected error occurred loading data from {filepath}.")
        return []

def save_items(filepath, items):
    """Saves items to a JSON file."""
    try:
        with open(filepath, "w") as f:
            json.dump(items, f, indent=2)
    except IOError as e:
        logging.error(f"Error saving items to {filepath}: {e}")
        st.error(f"Error saving data to {filepath}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred saving {filepath}: {e}")
        st.error(f"An unexpected error occurred saving data to {filepath}.")

# --- Streamlit App ---

st.set_page_config(layout="wide", page_title="CRM Review Dashboard")

st.title("📬 CRM Review Dashboard")
st.markdown("Review suggested CRM updates from incoming emails.")

# Load items for the current session
review_items = load_items(REVIEW_FILE)
archive_items = load_items(ARCHIVE_FILE) # Load archive to potentially display later

# Display current queue
st.header("Pending Review Queue")

if not review_items:
    st.info("No items to review at the moment. Great job, or waiting for new suggestions!")
else:
    # Use a counter for unique keys, especially important after pop()
    # Streamlit re-runs the script from top to bottom
    # We need to re-index after pop() or use a unique ID from the item itself
    # For simplicity, we'll re-index on each run since pop() re-arranges the list
    # A database would manage stable IDs better.

    st.subheader(f"Current Items ({len(review_items)})")

    # Display items in reverse order to make pop() less disruptive to the loop indexing
    for i in range(len(review_items) - 1, -1, -1):
        item = review_items[i]
        
        # Unique identifier for the item for Streamlit keys
        # Assuming email_subject and sender are unique enough, or add a generated ID in your data source
        item_key_prefix = f"{item['email_subject'].replace(' ', '_')}_{item['sender'].replace('.', '_')}_{i}"

        with st.expander(f"**Subject:** {item['email_subject']} | **From:** {item['sender']} | **Added:** {item.get('timestamp_added', 'N/A')}", expanded=True):
            st.markdown(f"**Email Body:**")
            st.markdown(item['email_body'])

            st.markdown("---")
            st.subheader("Proposed CRM Updates:")

            # Editable fields with current values
            col_status, col_note = st.columns(2)
            with col_status:
                status_input = st.text_input("Proposed Status", value=item.get('status', ''), key=f"status_{item_key_prefix}")
            with col_note:
                note_input = st.text_area("CRM Note", value=item.get('note', ''), key=f"note_{item_key_prefix}")

            task_desc_input = st.text_input("Task Description", value=item.get('task_description', ''), key=f"task_{item_key_prefix}")
            create_task_checkbox = st.checkbox("Create Task in CRM?", value=item.get('create_task', False), key=f"create_task_{item_key_prefix}")

            st.markdown("---")
            col_approve, col_reject = st.columns(2)

            with col_approve:
                if st.button("✅ Approve & Push to CRM", key=f"approve_btn_{item_key_prefix}", use_container_width=True):
                    # Update item with potentially edited values before pushing and archiving
                    item['status'] = status_input
                    item['note'] = note_input
                    item['task_description'] = task_desc_input
                    item['create_task'] = create_task_checkbox

                    try:
                        update_crm(
                            contact_email=item['sender'], # Or use a more reliable contact ID from item
                            status=item['status'],
                            note=item['note'],
                            task_desc=item['task_description'] if item['create_task'] else None
                        )
                        st.success(f"Successfully pushed '{item['email_subject']}' to CRM and removed from queue!")

                        # Archive the item after successful push
                        archived_item = item # Use the item with potentially updated values
                        archived_item['review_status'] = 'Approved'
                        archived_item['review_timestamp'] = datetime.now().isoformat() # ISO format for easy parsing

                        archive_items.append(archived_item)
                        save_items(ARCHIVE_FILE, archive_items)

                        review_items.pop(i) # Remove from current queue
                        save_items(REVIEW_FILE, review_items)
                        st.experimental_rerun() # Rerun to refresh the list
                    except Exception as e:
                        logging.error(f"CRM push failed for item '{item['email_subject']}': {e}", exc_info=True)
                        st.error(f"Failed to push to CRM. Error: {e}. This item remains in the queue for re-attempt or manual action.")

            with col_reject:
                if st.button("❌ Reject & Remove", key=f"reject_btn_{item_key_prefix}", use_container_width=True):
                    # Archive the item as rejected
                    rejected_item = review_items.pop(i)
                    rejected_item['review_status'] = 'Rejected'
                    rejected_item['review_timestamp'] = datetime.now().isoformat()

                    archive_items.append(rejected_item)
                    save_items(ARCHIVE_FILE, archive_items)

                    save_items(REVIEW_FILE, review_items)
                    st.warning(f"Item '{rejected_item['email_subject']}' rejected and moved to archive.")
                    st.experimental_rerun() # Rerun to refresh the list

# --- Optional: Display Archive (Can be a separate tab/section) ---
st.markdown("---")
if st.checkbox("Show Archived Items"):
    st.header("Archived Review Items")
    if not archive_items:
        st.info("No items in the archive yet.")
    else:
        # Sort by review_timestamp descending for most recent first
        sorted_archive = sorted(archive_items, key=lambda x: x.get('review_timestamp', ''), reverse=True)
        for j, item in enumerate(sorted_archive):
            with st.expander(f"**{item.get('review_status', 'N/A')}** - {item['email_subject']} from {item['sender']} ({item.get('review_timestamp', 'N/A')})"):
                st.markdown(f"**Original Email Body:** {item['email_body']}")
                st.markdown(f"**Final Status:** {item.get('status', 'N/A')}")
                st.markdown(f"**Final Note:** {item.get('note', 'N/A')}")
                st.markdown(f"**Task Created?:** {'Yes' if item.get('create_task', False) else 'No'}")
                if item.get('create_task'):
                    st.markdown(f"**Task Description:** {item.get('task_description', 'N/A')}")