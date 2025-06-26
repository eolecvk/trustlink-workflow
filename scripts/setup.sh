#!/bin/bash

set -e

# Function to check if a command exists
command_exists() {
  command -v "$1" &> /dev/null
}

echo "🚀 Starting Supabase Docker project setup..."

# --- Install Git if not present ---
echo "---"
if command_exists git; then
  echo "✅ Git is already installed. Skipping Git installation."
else
  echo "🔧 Installing Git..."
  sudo apt-get update -y && sudo apt-get install -y git
  echo "✅ Git installed."
fi

# --- Install Docker if not present and ensure user has permissions ---
echo "---"
if command_exists docker && docker info &> /dev/null; then
  echo "✅ Docker is already installed and accessible. Skipping Docker installation."
else
  echo "🔧 Installing Docker..."

  # Remove old Docker versions
  echo "🧼 Removing old Docker versions if any..."
  for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
    sudo apt-get remove -y "$pkg" || true
  done

  # Add Docker's official GPG key and repository
  echo "🔑 Adding Docker GPG key and repository..."
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
  sudo chmod a+r /etc/apt/keyrings/docker.asc

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  # Install Docker components
  echo "🐳 Installing Docker packages..."
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # Add current user to the 'docker' group
  echo "👥 Adding current user '$USER' to the 'docker' group for daemon access..."
  sudo usermod -aG docker "$USER"

  echo ""
  echo "--- IMPORTANT ---"
  echo "Docker has been installed and your user '$USER' has been added to the 'docker' group."
  echo "For these changes to take full effect, **you must log out of your current terminal session and log back in.**"
  echo "After logging back in, please re-run this script to continue with the Supabase project setup."
  echo "-----------------"
  exit 0 # Exit so user can re-login
fi

# --- Supabase Project Setup ---
echo "---"
echo "📁 Setting up Supabase Docker project..."

SUPABASE_DIR="supabase-project"
DOCKER_COMPOSE_FILE="$SUPABASE_DIR/docker-compose.yml"
ENV_EXAMPLE_FILE="$SUPABASE_DIR/.env"

if [ -d "$SUPABASE_DIR" ] && [ -f "$DOCKER_COMPOSE_FILE" ]; then
  echo "✅ Supabase project directory '$SUPABASE_DIR' already exists. Skipping download of Docker Compose files."
else
  echo "⬇️ Downloading Supabase Docker Compose files into '$SUPABASE_DIR'..."
  mkdir -p "$SUPABASE_DIR"
  curl -fsSL https://raw.githubusercontent.com/supabase/supabase/master/docker/docker-compose.yml -o "$DOCKER_COMPOSE_FILE"
  curl -fsSL https://raw.githubusercontent.com/supabase/supabase/master/docker/.env.example -o "$ENV_EXAMPLE_FILE"
  echo "✅ Docker Compose files downloaded."
fi

# Navigate into the Supabase project directory
cd "$SUPABASE_DIR" || { echo "❌ Failed to change directory to '$SUPABASE_DIR'. Exiting."; exit 1; }

echo "---"
echo "📦 Pulling Docker images for Supabase..."
# Check if docker compose command works without sudo before proceeding
if ! docker compose pull; then
  echo "❌ Failed to pull Docker images. This might be due to incorrect Docker permissions."
  echo "Please ensure you have logged out and logged back in after Docker installation."
  echo "You can try running 'docker compose pull' manually in the '$SUPABASE_DIR' directory."
  exit 1
fi
echo "✅ Docker images pulled successfully."

echo "---"
echo "⬆️ Bringing up Supabase services..."
if ! docker compose up -d; then
  echo "❌ Failed to start Supabase services."
  echo "Please check the Docker logs for more information or try 'docker compose up -d' manually."
  exit 1
fi
echo "✅ Supabase services are now running in the background."

echo "---"
echo "🎉 Supabase project setup complete!"
echo "You can access Supabase Studio at: \`http://localhost:8000\`"
echo "The Supabase project files are located in the \`./supabase-project\` directory."
echo ""
echo "To stop Supabase, navigate to the \`supabase-project\` directory and run: \`docker compose down\`"
echo "To restart Supabase, navigate to the \`supabase-project\` directory and run: \`docker compose up -d\`"