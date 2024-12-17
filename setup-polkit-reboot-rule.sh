#!/bin/bash

set -e

log_info() {
  echo -e "\033[1;32m[INFO]\033[0m $1"
}

log_error() {
  echo -e "\033[1;31m[ERROR]\033[0m $1" >&2
}

log_warn() {
  echo -e "\033[1;33m[WARNING]\033[0m $1" >&2
}

if [ "$(id -u)" -ne 0 ]; then
  log_error "This script must be run as root or via sudo."
  exit 1
fi

POLKIT_RULE_FILE="/etc/polkit-1/rules.d/99-reboot-no-auth.rules"
POLKIT_SERVICE="polkit.service"

create_polkit_rule() {
  log_info "Creating Polkit rule at $POLKIT_RULE_FILE..."

  cat > "$POLKIT_RULE_FILE" <<- EOL
polkit.addRule(function(action, subject) {
    if ((action.id == "org.freedesktop.login1.power-off" || action.id == "org.freedesktop.login1.reboot") &&
        subject.isInGroup("sudo")) {
        return polkit.Result.YES;
    }
});
EOL

  log_info "Polkit rule created successfully."
}

restart_polkit_service() {
  log_info "Restarting the Polkit service to apply the new rule..."
  if systemctl restart "$POLKIT_SERVICE"; then
    log_info "Polkit service restarted successfully."
  else
    log_warn "Failed to restart the Polkit service. Please ensure the 'polkit' service is installed and running."
  fi
}

if [ -f "$POLKIT_RULE_FILE" ]; then
  log_warn "Polkit rule already exists at $POLKIT_RULE_FILE. Skipping rule creation."
else
  create_polkit_rule
fi

restart_polkit_service

log_info "Setup completed. Users in the 'sudo' group can now reboot/shut down without interactive authorization."
