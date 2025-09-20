#!/bin/bash
# Setup or Uninstall Picar-X Racer as a systemd service.
# Usage:
# - To install the service on boot: sudo ./setup-service.sh install
# - To uninstall the service: sudo ./setup-service.sh uninstall
# - To display this help: ./setup-service.sh help

SERVICE_NAME="picar_x_racer.service"
USER=$(logname)
GROUP=$(id -g "$USER")
USER_ID=$(id -u "$USER")
PROJECT_DIR=$(pwd)
LOG_DIR="/home/$USER/.cache/picar-x-racer/logs"
PYTHON_BINARY="$PROJECT_DIR/backend/.venv/bin/python3"
BACKEND_SCRIPT="$PROJECT_DIR/backend/run.py"

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

print_command_help() {
  case "$1" in
    install)
      echo "Usage: sudo ./setup-service.sh install"
      echo "Set up the Picar-X Racer systemd service to start on boot."
      ;;
    uninstall)
      echo "Usage: sudo ./setup-service.sh uninstall"
      echo "Uninstall the Picar-X Racer systemd service."
      ;;
    help)
      print_help
      ;;
    *)
      echo "No help available for '$1'. Use './setup-service.sh help' for general usage."
      ;;
  esac
}

if [[ "$1" == "--help" || "$2" == "--help" || "$1" == "-h" || "$2" == "-h" ]]; then
  print_help
  exit 0
fi

if [[ -z "$1" ]]; then
  echo "Error: No command provided. Use './setup-service.sh -h' for usage information."
  print_help
  exit 1
fi

COMMAND="$1"

case "$COMMAND" in
  help | -h | --help | h)
    print_help
    exit 0
    ;;

  uninstall | U | -U | u | -u)
    echo "Disabling and removing $SERVICE_NAME..."
    sudo systemctl stop "$SERVICE_NAME"
    sudo systemctl disable "$SERVICE_NAME"
    sudo rm -f "/etc/systemd/system/$SERVICE_NAME"
    sudo systemctl daemon-reload
    sudo systemctl reset-failed

    if [[ -d "$LOG_DIR" ]]; then
      echo "Removing log directory at $LOG_DIR..."
      sudo rm -rf "$LOG_DIR"
    else
      echo "Log directory $LOG_DIR not found. Skipping..."
    fi

    echo "$SERVICE_NAME has been uninstalled successfully."
    exit 0
    ;;

  install | i | -i)
    echo "Setting up the Picar-X Racer systemd service..."

    if [[ ! -f "Makefile" ]]; then
      echo "Error: This script must be run from the project root (where the Makefile is located)."
      exit 1
    fi

    if [[ ! -f "$PYTHON_BINARY" ]]; then
      echo "Error: Virtual environment not found in '$PROJECT_DIR/backend/.venv'."
      echo "Please set up the virtual environment before setting up the service."
      echo "You can use: 'bash ./backend/setup_env.sh'."
      exit 1
    fi

    if [[ ! -d "$LOG_DIR" ]]; then
      echo "Creating log directory at $LOG_DIR..."
      sudo mkdir -p "$LOG_DIR"
      sudo chown -R "$USER:$USER" "$LOG_DIR"
    fi

    echo "Setting up log files in $LOG_DIR..."
    touch "$LOG_DIR/app.log" "$LOG_DIR/error.log"

    echo "Setting permissions for $LOG_DIR..."
    sudo chown -R "$USER:$USER" "$LOG_DIR"
    chmod 640 "$LOG_DIR/app.log" "$LOG_DIR/error.log"
    chmod -R u+rwX "$LOG_DIR"

    if [[ -f "/etc/systemd/system/$SERVICE_NAME" ]]; then
      read -rp "Service $SERVICE_NAME already exists. Do you want to overwrite it? [y/N]: " confirm
      if [[ "$confirm" != "y" ]]; then
        echo "Cancelled setup."
        exit 0
      fi
    fi

    TMP_SERVICE_FILE="./$SERVICE_NAME"

    cat > "$TMP_SERVICE_FILE" << EOL
[Unit]
Description=Picar-X Racer Backend Service
After=network-online.target
Wants=network-online.target
After=sound.target
Requires=sound.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$PROJECT_DIR/backend
Environment=PYTHONUNBUFFERED=1
Environment=XDG_RUNTIME_DIR=/run/user/$USER_ID
Environment=DISPLAY=:0
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$USER_ID/bus
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
WantedBy=multi-user.target
EOL

    echo "Installing $SERVICE_NAME to systemd..."
    sudo mv "$TMP_SERVICE_FILE" /etc/systemd/system/$SERVICE_NAME
    rm -f "$TMP_SERVICE_FILE"

    echo "Reloading systemd daemon..."
    sudo systemctl daemon-reload

    echo "Enabling $SERVICE_NAME to start on system boot..."
    sudo systemctl enable "$SERVICE_NAME"

    echo "Starting $SERVICE_NAME..."
    if sudo systemctl start "$SERVICE_NAME"; then
      echo "$SERVICE_NAME has started successfully!"
      echo "Logs can be found at: $LOG_DIR"
    else
      echo "Error: $SERVICE_NAME failed to start."
      echo "Run 'sudo journalctl -xe -u $SERVICE_NAME' for detailed logs."
      exit 1
    fi

    echo "To disable the service, run 'sudo systemctl disable $SERVICE_NAME'."
    echo "To stop the service, run 'sudo systemctl stop $SERVICE_NAME'."
    echo "To view logs, run 'sudo journalctl -u $SERVICE_NAME' or check $LOG_DIR."
    exit 0
    ;;

  *)
    echo "Error: Invalid command '$COMMAND'. Use './setup-service.sh help' for usage information."
    exit 1
    ;;
esac
