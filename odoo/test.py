import xmlrpc.client

# Configuration
url = "http://localhost:8069"  # Change if needed
db = "odoo"                    # Your Odoo database name
username = "test"              # Your Odoo username
password = "test"              # Your Odoo password

# Connect to Odoo
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
uid = common.authenticate(db, username, password, {})

if not uid:
    raise Exception("Authentication failed. Check DB name, username, and password.")

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)

def create_or_update_lead(email, name, phone=None):
    # Search for existing lead by email
    lead_ids = models.execute_kw(db, uid, password,
        'crm.lead', 'search',
        [[['email_from', '=', email]]])

    # Prepare lead data without None values
    lead_data = {
        'name': name,
        'email_from': email
    }
    if phone is not None:
        lead_data['phone'] = phone

    if lead_ids:
        # Update the existing lead
        models.execute_kw(db, uid, password, 'crm.lead', 'write', [
            lead_ids, lead_data
        ])
        print(f"Lead updated (ID: {lead_ids[0]})")
        return lead_ids[0]
    else:
        # Create a new lead
        lead_id = models.execute_kw(db, uid, password, 'crm.lead', 'create', [lead_data])
        print(f"Lead created (ID: {lead_id})")
        return lead_id

if __name__ == "__main__":
    create_or_update_lead("test@example.com", "Test User", phone=None)
