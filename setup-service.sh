#!/usr/bin/env bash
# Install the backend system service with access to the user's audio session.
set -euo pipefail

SERVICE_NAME="picar_x_racer.service"
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-help}"
case "$COMMAND" in
  help|-h|--help|h)
    cat <<HELP
Usage: sudo bash $0 install [user]
       sudo bash $0 uninstall
       bash $0 print [user]

Installs a system service running as the specified user (default: sudo caller).
Enables user-session linger for PipeWire audio at boot. 'print' previews the unit.
Uninstall preserves application data, logs, and user-session linger.
HELP
    exit 0 ;;
  install|i|-i|print|uninstall|U|-U|u|-u) ;;
  *) echo "Unknown command: $COMMAND" >&2; exit 1 ;;
esac
if [[ "$COMMAND" != print && $(id -u) -ne 0 ]]; then
  echo "Run installation or removal with sudo." >&2
  exit 1
fi
case "$COMMAND" in
  uninstall|U|-U|u|-u)
    systemctl disable --now "$SERVICE_NAME"
    rm -f "/etc/systemd/system/$SERVICE_NAME"
    systemctl daemon-reload
    exit 0 ;;
esac
SERVICE_USER="${2:-${SUDO_USER:-${USER:-}}}"
if [[ -z "$SERVICE_USER" || "$SERVICE_USER" == root ]]; then
  echo "Specify a non-root service user: sudo bash $0 install <user>" >&2
  exit 1
fi
SERVICE_UID="$(id -u "$SERVICE_USER")"
SERVICE_GROUP="$(id -gn "$SERVICE_USER")"
SERVICE_HOME="$(getent passwd "$SERVICE_USER" | cut -d: -f6)"
LOG_DIR="$SERVICE_HOME/.cache/picar-x-racer/logs"
PYTHON_BINARY="$PROJECT_DIR/backend/.venv/bin/python3"
render_unit() {
cat <<UNIT
[Unit]
Description=Picar-X Racer Backend Service
After=network-online.target sound.target user@$SERVICE_UID.service
Wants=network-online.target user@$SERVICE_UID.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR/backend
Environment=PYTHONUNBUFFERED=1
Environment=XDG_RUNTIME_DIR=/run/user/$SERVICE_UID
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$SERVICE_UID/bus
Environment=PULSE_SERVER=unix:/run/user/$SERVICE_UID/pulse/native
Environment=DISPLAY=:0
Environment="PATH=/usr/bin:/bin:/usr/local/bin"
Environment="HOME=$SERVICE_HOME"
Environment="PX_LOG_DIR=$LOG_DIR"
Environment=HAILO_MONITOR=0
Environment=HAILO_TRACE=0
Environment=HAILORT_LOGGER_PATH=NONE
ExecStart="$PYTHON_BINARY" "$PROJECT_DIR/backend/run.py"
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT
}
if [[ "$COMMAND" == print ]]; then
  render_unit
  exit 0
fi
if [[ ! -x "$PYTHON_BINARY" ]]; then
  echo "Create the backend environment first: bash $PROJECT_DIR/backend/setup_env.sh" >&2
  exit 1
fi
install -d -m 0750 -o "$SERVICE_USER" -g "$SERVICE_GROUP" "$LOG_DIR"
loginctl enable-linger "$SERVICE_USER"
systemctl start "user@$SERVICE_UID.service"
render_unit > "/etc/systemd/system/$SERVICE_NAME"
chmod 0644 "/etc/systemd/system/$SERVICE_NAME"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
systemctl --no-pager status "$SERVICE_NAME"
