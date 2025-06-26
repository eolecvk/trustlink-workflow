#!/bin/bash

# Get the absolute path to the parent directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Clone supabase repo next to the parent dir of the script
if [ ! -d "$PARENT_DIR/supabase/.git" ]; then
  git clone --depth 1 https://github.com/supabase/supabase "$PARENT_DIR/supabase"
else
  echo "Supabase repo already exists, skipping clone."
fi

# Create the project directory
mkdir -p "$PARENT_DIR/supabase-project"

# Copy docker files into the new project directory
cp -rf "$PARENT_DIR/supabase/docker/"* "$PARENT_DIR/supabase-project"
cp "$PARENT_DIR/supabase/docker/.env.example" "$PARENT_DIR/supabase-project/.env"

# Move into the new project directory
cd "$PARENT_DIR/supabase-project" || exit 1

# Pull and start the containers
docker compose pull
docker compose up -d
