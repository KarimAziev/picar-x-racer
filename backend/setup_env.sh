#!/bin/bash

echo "Installing portaudio19-dev, sox and libsox-fmt-mp3"
sudo apt-get install portaudio19-dev sox libsox-fmt-mp3 -y
echo "Creating venv"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Check if the OS is Raspbian
if ! grep -q "Raspbian" /etc/os-release; then
  echo "This is not a Raspbian OS. Setting up IDE environment..."
  echo "Installing dev dependencies."
  pip install -r requirements-dev.txt
  echo "IDE environment setup completed."
else
  echo "This is a Raspbian OS. Standard installation will proceed."
  pip install -r requirements.txt
fi
