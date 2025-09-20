#!/bin/bash
# Setup or Uninstall Picar-X Racer as a systemd user service (with linger).
# Usage:
#   sudo ./setup-service.sh install
#   sudo ./setup-service.sh uninstall
#   ./setup-service.sh help

SERVICE_NAME="picar_x_racer.service"
USER=$(logname)
USER_ID=$(id -u "$USER")
RUNTIME_DIR="/run/user/$USER_ID"
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
    if ! sudo loginctl enable-linger "$USER"; then
      echo "Warning: failed to enable linger for $USER (continuing)"
    fi

    if [[ ! -d "$RUNTIME_DIR" ]]; then
      echo "Creating runtime dir $RUNTIME_DIR..."
      sudo mkdir -p "$RUNTIME_DIR"
      sudo chown "$USER:$USER" "$RUNTIME_DIR"
      sudo chmod 700 "$RUNTIME_DIR"
    fi

    export XDG_RUNTIME_DIR="$RUNTIME_DIR"

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

    echo "Attempting to enable/start the user service for $USER..."

    print_manual_instructions() {
      cat << MSG

Could not start the user service automatically from this script.
Possible causes:
  - There is no per-user dbus/systemd session available for $USER right now.
  - dbus-run-session (dbus-user-session package) is not installed.

You can either:
  1) Log in once as $USER (SSH/console) and run:
       systemctl --user daemon-reload
       systemctl --user enable --now $SERVICE_NAME

  2) Or run this one-liner as root to start it now using a transient session (requires dbus-run-session):
       sudo -u $USER dbus-run-session --systemd -- /bin/bash -lc "systemctl --user daemon-reload && systemctl --user enable --now $SERVICE_NAME"

To install dbus-run-session on Debian/Bookworm:
  apt-get update && apt-get install -y dbus-user-session

View logs after starting with:
  sudo -u $USER journalctl --user -u $SERVICE_NAME -f

MSG
    }

    if sudo -u "$USER" bash -c 'command -v dbus-run-session >/dev/null 2>&1'; then
      if sudo -u "$USER" dbus-run-session --help 2>&1 | grep -q -- '--systemd'; then
        echo "Using dbus-run-session --systemd to start a transient user manager..."
        if sudo -u "$USER" env XDG_RUNTIME_DIR="$RUNTIME_DIR" dbus-run-session --systemd -- /bin/bash -lc "systemctl --user daemon-reload && systemctl --user enable --now '$SERVICE_NAME'"; then
          echo "Service enabled and started as user $USER (via dbus-run-session --systemd)."
          echo "View logs with: sudo -u $USER journalctl --user -u $SERVICE_NAME -f"
          exit 0
        else
          echo "Failed to start service via dbus-run-session --systemd."
        fi
      else
        echo "dbus-run-session present but does not support --systemd. Trying fallback: start systemd --user inside dbus-run-session..."
        if sudo -u "$USER" env XDG_RUNTIME_DIR="$RUNTIME_DIR" dbus-run-session -- /bin/bash -lc \
          "nohup systemd --user >/dev/null 2>&1 & sleep 0.6; systemctl --user daemon-reload && systemctl --user enable --now '$SERVICE_NAME'"; then
          echo "Service enabled and started as user $USER (via dbus-run-session + systemd --user)."
          echo "View logs with: sudo -u $USER journalctl --user -u $SERVICE_NAME -f"
          exit 0
        else
          echo "Failed to start service via dbus-run-session + systemd --user fallback."
        fi
      fi
    fi

    if sudo -u "$USER" env XDG_RUNTIME_DIR="$RUNTIME_DIR" systemctl --user daemon-reload &> /dev/null; then
      if sudo -u "$USER" env XDG_RUNTIME_DIR="$RUNTIME_DIR" systemctl --user enable --now "$SERVICE_NAME"; then
        echo "Service enabled and started as user $USER."
        echo "View logs with: sudo -u $USER journalctl --user -u $SERVICE_NAME -f"
        exit 0
      else
        echo "Failed to enable/start unit via systemctl --user."
        print_manual_instructions
        exit 0
      fi
    else
      echo "No per-user systemd instance available for $USER right now."
      print_manual_instructions
      exit 0
    fi

    echo "Setup complete."
    exit 0
    ;;

  *)
    echo "Error: Invalid command '$COMMAND'. Use './setup-service.sh help' for usage information."
    exit 1
    ;;
esac
