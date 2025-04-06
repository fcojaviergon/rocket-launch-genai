#!/bin/bash

# Script to help setup environment variables for different environments

# Default environment is development
ENV_TYPE=${1:-development}
COMPONENT=${2:-both}

# Validate environment input
if [[ ! "$ENV_TYPE" =~ ^(development|staging|production|test)$ ]]; then
  echo "Error: Invalid environment type."
  echo "Usage: $0 [development|staging|production|test] [backend|frontend|both]"
  exit 1
fi

# Validate component input
if [[ ! "$COMPONENT" =~ ^(backend|frontend|both)$ ]]; then
  echo "Error: Invalid component."
  echo "Usage: $0 [development|staging|production|test] [backend|frontend|both]"
  exit 1
fi

# Base directory is the project root
BASE_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
cd "$BASE_DIR" || exit 1

# Function to setup env for a specific component
setup_component_env() {
  local component=$1
  local env_type=$2
  
  echo "Setting up $component environment for $env_type..."
  
  cd "$BASE_DIR/$component" || exit 1
  
  # Check if .env.example exists
  if [ ! -f ".env.example" ]; then
    echo "Error: .env.example file not found for $component."
    return 1
  fi
  
  # Check if target .env file already exists
  TARGET_ENV_FILE=".env.$env_type"
  if [ -f "$TARGET_ENV_FILE" ]; then
    read -p "$TARGET_ENV_FILE already exists for $component. Overwrite? (y/n): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
      echo "Skipping $component environment setup."
      return 0
    fi
  fi
  
  # Copy .env.example to target .env file
  cp ".env.example" "$TARGET_ENV_FILE"
  echo "Created $TARGET_ENV_FILE from .env.example for $component"
  
  # Create symlink to .env for local development
  if [ "$env_type" = "development" ]; then
    if [ -L ".env" ] || [ -f ".env" ]; then
      rm ".env"
    fi
    ln -s "$TARGET_ENV_FILE" ".env"
    echo "Created symlink from .env to $TARGET_ENV_FILE for $component"
  fi
  
  echo "$component environment setup complete for $env_type."
  echo ""
}

# Setup environment based on component selection
if [ "$COMPONENT" = "backend" ] || [ "$COMPONENT" = "both" ]; then
  setup_component_env "backend" "$ENV_TYPE"
fi

if [ "$COMPONENT" = "frontend" ] || [ "$COMPONENT" = "both" ]; then
  setup_component_env "frontend" "$ENV_TYPE"
fi

# Help user with next steps
echo ""
echo "Next steps:"
echo "1. Edit the .env.$ENV_TYPE files to set proper values for your $ENV_TYPE environment"
echo "2. For local machine-specific settings, create .env.$ENV_TYPE.local (this file will not be committed to git)"

if [ "$ENV_TYPE" = "production" ]; then
  echo ""
  echo "IMPORTANT: For production environment:"
  echo "- Generate strong passwords and secrets"
  echo "- Secure your database credentials"
  echo "- Set appropriate API keys"
  echo "- Make sure the environment files are secured and not committed to version control"
fi

echo ""
echo "Done! Environment file setup complete." 