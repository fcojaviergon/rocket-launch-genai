#!/bin/bash

# Script to help setup environment variables for different environments

# Default environment is development
ENV_TYPE=${1:-development}

# Validate input
if [[ ! "$ENV_TYPE" =~ ^(development|staging|production|test)$ ]]; then
  echo "Error: Invalid environment type."
  echo "Usage: $0 [development|staging|production|test]"
  exit 1
fi

# Base directory is the project root
BASE_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
cd "$BASE_DIR" || exit 1

# Check if .env.example exists
if [ ! -f ".env.example" ]; then
  echo "Error: .env.example file not found."
  exit 1
fi

# Check if target .env file already exists
TARGET_ENV_FILE=".env.$ENV_TYPE"
if [ -f "$TARGET_ENV_FILE" ]; then
  read -p "$TARGET_ENV_FILE already exists. Overwrite? (y/n): " OVERWRITE
  if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
    echo "Operation cancelled."
    exit 0
  fi
fi

# Copy .env.example to target .env file
cp ".env.example" "$TARGET_ENV_FILE"
echo "Created $TARGET_ENV_FILE from .env.example"

# Create symlink to .env for local development
if [ "$ENV_TYPE" = "development" ]; then
  if [ -L ".env" ] || [ -f ".env" ]; then
    rm ".env"
  fi
  ln -s "$TARGET_ENV_FILE" ".env"
  echo "Created symlink from .env to $TARGET_ENV_FILE"
fi

# Help user with next steps
echo ""
echo "Next steps:"
echo "1. Edit $TARGET_ENV_FILE to set proper values for your $ENV_TYPE environment"
echo "2. For local machine-specific settings, create .env.$ENV_TYPE.local (this file will not be committed to git)"

if [ "$ENV_TYPE" = "production" ]; then
  echo ""
  echo "IMPORTANT: For production environment:"
  echo "- Generate strong passwords and secrets"
  echo "- Secure your database credentials"
  echo "- Set appropriate API keys"
  echo "- Make sure the environment file is secured and not committed to version control"
fi

echo ""
echo "Done! Environment file setup complete for $ENV_TYPE environment." 