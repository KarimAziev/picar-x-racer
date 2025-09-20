#!/bin/bash
# Setup or Uninstall Picar-X Racer as a systemd user service (with linger).
# Usage:
#   sudo ./setup-service.sh install
#   sudo ./setup-service.sh uninstall
#   ./setup-service.sh help

SERVICE_NAME="picar_x_racer.service"
USER=$(logname)
PROJECT_DIR=$(pwd)
LOG_DIR="/home/$USER/.cache/picar-x-racer/logs"
PYTHON_BINARY="$PROJECT_DIR/backend/.venv/bin/python3"
BACKEND_SCRIPT="$PROJECT_DIR/backend/run.py"
USER_UNIT_DIR="/home/$USER/.config/systemd/user"
USER_UNIT_FILE="$USER_UNIT_DIR/$SERVICE_NAME"
SYSTEM_UNIT_FILE="/etc/systemd/system/$SERVICE_NAME"

print_help() {
  cat << EOF
Usage: sudo ./setup-service.sh [command]

Setup or Uninstall Picar-X Racer as a systemd user service (with linger).

Commands:
  install, i, -i        Install the Picar-X Racer as a systemd --user service and enable linger.
  uninstall, U, -U, u   Uninstall both system and user service files.
  help, -h, --help      Show this message.
EOF
}

if [[ "$1" == "--help" || "$2" == "--help" || "$1" == "-h" || "$2" == "-h" ]]; then
  print_help
  exit 0
fi

if [[ -z "$1" ]]; then
  echo "Error: No command provided. Use './setup-service.sh help' for usage information."
  exit 1
fi

COMMAND="$1"

case "$COMMAND" in
  help | -h | --help | h)
    print_help
    exit 0
    ;;

  uninstall | U | -U | u | -u)
    echo "Uninstalling Picar-X Racer service..."

    if sudo -u "$USER" systemctl --user status "$SERVICE_NAME" &> /dev/null; then
      echo "Stopping user service..."
      sudo -u "$USER" systemctl --user stop "$SERVICE_NAME" || true
      sudo -u "$USER" systemctl --user disable "$SERVICE_NAME" || true
    fi
    if [[ -f "$USER_UNIT_FILE" ]]; then
      echo "Removing user unit at $USER_UNIT_FILE"
      sudo rm -f "$USER_UNIT_FILE"
    fi
    sudo -u "$USER" systemctl --user daemon-reload || true

    if [[ -f "$SYSTEM_UNIT_FILE" ]]; then
      echo "Stopping and removing system unit..."
      sudo systemctl stop "$SERVICE_NAME" || true
      sudo systemctl disable "$SERVICE_NAME" || true
      sudo rm -f "$SYSTEM_UNIT_FILE"
      sudo systemctl daemon-reload
      sudo systemctl reset-failed
    fi

    if [[ -d "$LOG_DIR" ]]; then
      echo "Removing log directory at $LOG_DIR..."
      sudo rm -rf "$LOG_DIR"
    else
      echo "Log directory $LOG_DIR not found. Skipping..."
    fi

    echo "Uninstall complete."
    exit 0
    ;;

  install | i | -i)
    echo "Setting up the Picar-X Racer systemd user service for user $USER..."

    if [[ ! -f "Makefile" ]]; then
      echo "Error: This script must be run from the project root (where the Makefile is located)."
      exit 1
    fi

    if [[ ! -f "$PYTHON_BINARY" ]]; then
      echo "Error: Virtual environment not found in '$PROJECT_DIR/backend/.venv'."
      echo "Please set up the virtual environment before setting up the service."
      exit 1
    fi

    if [[ ! -d "$LOG_DIR" ]]; then
      echo "Creating log directory at $LOG_DIR..."
      sudo mkdir -p "$LOG_DIR"
      sudo chown -R "$USER:$USER" "$LOG_DIR"
    fi

    touch "$LOG_DIR/app.log" "$LOG_DIR/error.log"
    sudo chown -R "$USER:$USER" "$LOG_DIR"
    chmod 640 "$LOG_DIR/app.log" "$LOG_DIR/error.log"
    chmod -R u+rwX "$LOG_DIR"

    echo "Enabling linger for user $USER..."
    sudo loginctl enable-linger "$USER" || {
      echo "Warning: failed to enable linger for $USER"
    }

    echo "Creating user unit directory at $USER_UNIT_DIR..."
    sudo -u "$USER" mkdir -p "$USER_UNIT_DIR"

    cat > "./$SERVICE_NAME" << EOL
[Unit]
Description=Picar-X Racer Backend Service (user)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR/backend
Environment=PYTHONUNBUFFERED=1
Environment="PATH=/usr/bin:/bin:/usr/local/bin"
Environment=HOME=/home/$USER
Environment=PX_LOG_DIR=$LOG_DIR
Environment=HAILO_MONITOR=0
Environment=HAILO_TRACE=0
Environment=HAILORT_LOGGER_PATH=NONE
ExecStart=$PYTHON_BINARY $BACKEND_SCRIPT
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOL

    echo "Installing user unit to $USER_UNIT_FILE..."
    sudo mv "./$SERVICE_NAME" "$USER_UNIT_FILE"
    sudo chown "$USER:$USER" "$USER_UNIT_FILE"
    sudo -u "$USER" systemctl --user daemon-reload

    echo "Enabling and starting the user service..."
    if sudo -u "$USER" systemctl --user enable --now "$SERVICE_NAME"; then
      echo "Service enabled and started as user $USER."
      echo "Logs: journalctl --user -u $SERVICE_NAME or $LOG_DIR"
    else
      echo "Failed to start the user service. Run 'sudo -u $USER systemctl --user status $SERVICE_NAME' or check journalctl."
      exit 1
    fi

    echo "Setup complete."
    exit 0
    ;;

  *)
    echo "Error: Invalid command '$COMMAND'. Use './setup-service.sh help' for usage information."
    exit 1
    ;;
esac
