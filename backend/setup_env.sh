#!/bin/sh

set -e

log_info() {
  printf "\033[32m[INFO]\033[0m %s\n" "$1"
}
log_error() {
  printf "\033[31m[ERROR]\033[0m %s\n" "$1" >&2
}

command_exists() {
  command -v "$1" > /dev/null 2>&1
}

if ! command_exists apt-get; then
  log_error "This script requires 'apt-get', but it was not found. Aborting."
  exit 1
fi

log_info "Installing portaudio19-dev, sox, libsox-fmt-mp3, and ffmpeg..."
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
else
  SUDO=""
fi
$SUDO apt-get update
$SUDO apt-get install -y portaudio19-dev sox libsox-fmt-mp3 ffmpeg

if ! command_exists python3; then
  log_error "Python 3 is not installed or not in PATH. Please install it and try again."
  exit 1
fi

if [ -d ".venv" ]; then
  log_info "Virtual environment '.venv' already exists. Skipping creation."
else
  log_info "Creating Python virtual environment in '.venv'..."
  python3 -m venv .venv
fi

log_info "Activating Python virtual environment..."
# shellcheck disable=SC1091
. .venv/bin/activate

log_info "Upgrading pip..."
pip install --quiet --upgrade pip

if [ ! -f "requirements.txt" ]; then
  log_error "requirements.txt file not found. Please ensure it exists in the current directory."
  exit 1
fi

log_info "Installing dependencies from requirements.txt..."
pip install --quiet -r requirements.txt

is_raspberry_pi() {
  if [ -f /proc/device-tree/model ]; then
    if grep -qi "raspberry pi" /proc/device-tree/model; then
      return 0
    fi
  fi
  return 1
}

if is_raspberry_pi; then
  log_info "Raspberry Pi detected. Standard installation complete."
else
  log_info "Non-Raspberry Pi system detected. Setting up IDE environment..."
  if [ ! -f "requirements-dev.txt" ]; then
    log_error "requirements-dev.txt file not found. Please ensure it exists in the current directory."
    exit 1
  fi
  log_info "Installing development dependencies from requirements-dev.txt..."
  pip install --quiet -r requirements-dev.txt
  log_info "IDE environment setup completed."
fi

log_info "Setup completed successfully!"
