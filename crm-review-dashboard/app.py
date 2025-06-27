"""
Streamlit app
"""

import streamlit as st
import json
from crm.push_update import update_crm

REVIEW_FILE = "data/review_queue.json"

def load_review_items():
    with open(REVIEW_FILE, "r") as f:
        return json.load(f)

def save_review_items(items):
    with open(REVIEW_FILE, "w") as f:
        json.dump(items, f, indent=2)

st.title("📬 CRM Review Dashboard")

items = load_review_items()

if not items:
    st.info("No items to review.")
else:
    for i, item in enumerate(items):
        with st.expander(f"{item['email_subject']} from {item['sender']}"):
            st.markdown(f"**Body:** {item['email_body']}")
            status = st.text_input("Proposed Status", value=item['status'], key=f"status_{i}")
            note = st.text_area("CRM Note", value=item['note'], key=f"note_{i}")
            task_desc = st.text_input("Task Description", value=item['task_description'], key=f"task_{i}")
            create_task = st.checkbox("Create Task?", value=item['create_task'], key=f"create_{i}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve", key=f"approve_{i}"):
                    update_crm(
                        contact_email=item['sender'],
                        status=status,
                        note=note,
                        task_desc=task_desc if create_task else None
                    )
                    st.success("Pushed to CRM")
                    items.pop(i)
                    save_review_items(items)
                    st.experimental_rerun()
            with col2:
                if st.button("❌ Reject", key=f"reject_{i}"):
                    items.pop(i)
                    save_review_items(items)
                    st.warning("Item rejected")
                    st.experimental_rerun()
