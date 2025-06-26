#!/bin/bash

set -e

echo "🔧 Installing Docker and Git..."
sudo apt-get update -y
sudo apt-get install -y git ca-certificates curl gnupg lsb-release

echo "🧼 Removing old Docker versions if any..."
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt-get remove -y $pkg || true
done

echo "🔑 Adding Docker GPG key and repository..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "🐳 Installing Docker..."
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "🚀 Verifying Docker installation..."
sudo docker run --rm hello-world

echo "📁 Setting up Supabase Docker project..."
mkdir -p supabase-project
curl -fsSL https://raw.githubusercontent.com/supabase/supabase/master/docker/docker-compose.yml -o supabase-project/docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/supabase/supabase/master/docker/.env.example -o supabase-project/.env

cd supabase-project
docker compose pull
docker compose up -d

echo "✅ Supabase is running!"
