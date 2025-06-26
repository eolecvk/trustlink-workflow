# trustlink-workflow


## Setup

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m ensurepip --upgrade
```

## Run

```bash
source venv/bin/activate
python outlook_read_emails.py
```

## Atomic CRM

Install
```
git clone https://github.com/[username]/atomic-crm.git
cd atomic-crm
make install
```

Run locally
```
make start
```

Access frontend & create first user : http://localhost:5173/.


If you need debug the backend, you can access the following services:  
* Supabase dashboard: http://localhost:54323/
* REST API: http://127.0.0.1:54321
* Attachments storage: http://localhost:54323/project/default/storage/buckets/attachments
* Inbucket email testing service: http://localhost:54324/



## Supabase deploy

```
sudo chmod +x scripts/setup.sh
./scripts/setup.sh
```

optionally, check:
```
docker compose ls
```

Navigate to http://localhost:54323

(Dropping NocoDB UI for now as it makes things more complex)


## Atomic CRM

