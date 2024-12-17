#!/bin/bash
# Setup or Uninstall Picar-X Racer as a systemd service.
# Usage:
# - To setup the service on boot: sudo ./setup-service.sh setup
# - To uninstall the service: sudo ./setup-service.sh uninstall
# - To display this help: ./setup-service.sh help

SERVICE_NAME="picar_x_racer.service"
USER=$(whoami)
PROJECT_DIR=$(pwd)
LOG_DIR="/var/log/picar_x_racer"
PYTHON_BINARY="$PROJECT_DIR/backend/.venv/bin/python3"
BACKEND_SCRIPT="$PROJECT_DIR/backend/run.py"

print_help() {
  echo "Usage: sudo ./setup-service.sh [command]"
  echo ""
  echo "Commands:"
  echo "  setup      Set up the Picar-X Racer systemd service to start on boot."
  echo "  uninstall  Uninstall the Picar-X Racer systemd service."
  echo "  help       Display this help message."
  echo ""
  echo "Examples:"
  echo "  sudo ./setup-service.sh setup"
  echo "  sudo ./setup-service.sh uninstall"
  echo "  ./setup-service.sh help"
}

print_command_help() {
  case "$1" in
    setup)
      echo "Usage: sudo ./setup-service.sh setup"
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

if [[ "$1" == "--help" || "$2" == "--help" ]]; then
  if [[ -n "$1" && "$1" != "--help" ]]; then
    print_command_help "$1"
  else
    print_help
  fi
  exit 0
fi

if [[ -z "$1" ]]; then
  echo "Error: No command provided. Use './setup-service.sh help' for usage information."
  exit 1
fi

COMMAND="$1"

case "$COMMAND" in
  help)
    print_help
    exit 0
    ;;

  uninstall)
    echo "Disabling and removing $SERVICE_NAME..."
    sudo systemctl stop "$SERVICE_NAME"
    sudo systemctl disable "$SERVICE_NAME"
    sudo rm -f "/etc/systemd/system/$SERVICE_NAME"
    sudo systemctl daemon-reload
    sudo systemctl reset-failed
    echo "$SERVICE_NAME has been uninstalled."
    exit 0
    ;;

  setup)
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
    fi

    echo "Setting up log files in $LOG_DIR..."
    sudo touch "$LOG_DIR/picar_x_racer.log" "$LOG_DIR/picar_x_racer_error.log"
    sudo chmod 640 "$LOG_DIR/picar_x_racer.log" "$LOG_DIR/picar_x_racer_error.log"
    sudo chown -R "$USER:adm" "$LOG_DIR"

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

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
Environment=HOME=/home/$USER
ExecStart=$PYTHON_BINARY $BACKEND_SCRIPT
Restart=always
StandardOutput=append:$LOG_DIR/picar_x_racer.log
StandardError=append:$LOG_DIR/picar_x_racer_error.log

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
      echo "Logs can be found at: $LOG_DIR/picar_x_racer.log"
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
