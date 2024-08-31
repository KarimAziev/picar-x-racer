#!/bin/bash

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Check if the OS is Raspbian
if ! grep -q "Raspbian" /etc/os-release; then
  echo "This is not a Raspbian OS. Setting up IDE environment..."
  # Return to the scripts directory
  echo "Installing dependencies."
  pip install -r requirements.txt
  echo "Installing dev dependencies."
  pip install -r requirements-dev.txt
  echo "IDE environment setup completed."
else
  echo "This is a Raspbian OS. Standard installation will proceed."
  pip install -r requirements.txt
fi
