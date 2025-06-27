# CRM automation

Self-hosted AI-powered CRM with integration to mailbox

## Setup

* Install Git
* Install Docker
* Python env

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

### `N8N` 

n8n

Dev
```bash
docker volume create n8n-data
docker run -it \
  --name n8n \
  -p 5678:5678 \
  -v n8n-data:/home/node/.n8n \
  -e N8N_CUSTOM_EXTENSIONS='/home/node/.n8n/custom' \
  -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
  -e N8N_RUNNERS_ENABLED=true \
  -e N8N_DATA_FOLDER=/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

http://localhost:5678


Prod
```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v "$(pwd)/.n8n:/home/node/.n8n" \
  -e N8N_CUSTOM_EXTENSIONS='/home/node/.n8n/custom' \
  -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
  -e N8N_RUNNERS_ENABLED=true \
  -e N8N_DATA_FOLDER=/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

Install `n8n-nodes-twenty` through:
```
Settings > Commmunity Nodes > "n8n-nodes-twenty"
```
(look into manual install later? https://docs.n8n.io/integrations/community-nodes/installation/manual-install/)


## Odoo

```bash
docker run -p 8069:8069 --name odoo \
  -t odoo:16 \
  --db_user=odoo --db_password=odoo --db_host=host.docker.internal
```

Next setup Outlook - Odoo
* Option 1: Odoo native connector
* Option 2: N8N Outlook to Odoo



## Twenty CRM (self-hosted) -- To be continued


```bash
bash <(curl -sL https://raw.githubusercontent.com/twentyhq/twenty/main/packages/twenty-docker/scripts/install.sh)
```

Finalize deployment following steps at:
https://twenty.com/developers/section/self-hosting/docker-compose