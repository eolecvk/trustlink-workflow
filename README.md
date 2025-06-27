# trustlink-workflow


## Setup

Install python3.12
```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv -y
```

activate virtual environment
```bash
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
python -m ensurepip --upgrade
```

Check version
```bash
python --version  # should show Python 3.12.x
```

## Run

```bash
source venv/bin/activate
python outlook_read_emails.py
```

## Twenty CRM


### Twenty CRM self-hosted deployment


```bash
bash <(curl -sL https://raw.githubusercontent.com/twentyhq/twenty/main/packages/twenty-docker/scripts/install.sh)
```

Finalize deployment following steps at:
https://twenty.com/developers/section/self-hosting/docker-compose

### Twenty CRM API setup

* Generate API Key

* Data model (likely)

  + `GET /api/contacts` (to search for existing contacts)
  + `POST /api/contacts` (to create new contacts)
  + `PUT /api/contacts/{id}` (to update existing contacts)


------

# Deprecated

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

