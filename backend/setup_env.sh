#!/usr/bin/env bash
set -e
set -o pipefail

INTERACTIVE="non-interactive"
SKIP_PROMPT="yes"
SKIP_DBUS=0
SKIP_GSTREAMER=0
MINIMAL=0
DRY_RUN=0
POLKIT_RULE_FILE="/etc/polkit-1/rules.d/99-reboot-no-auth.rules"
POLKIT_SERVICE="polkit.service"

SYSTEM_SITE_PACKAGES=

log_info() {
  printf "\033[32m[INFO]\033[0m %s\n" "$1"
}

log_error() {
  printf "\033[31m[ERROR]\033[0m %s\n" "$1" >&2
}

log_warn() {
  echo -e "\033[1;33m[WARNING]\033[0m $1" >&2
}

is_raspberry_pi() {
  if [ -f /proc/device-tree/model ]; then
    if grep -qi "raspberry pi" /proc/device-tree/model; then
      return 0
    fi
  fi
  return 1
}
STEPS=(install_system_deps setup_gstreamer create_venv install_python_deps)
if is_raspberry_pi; then
  log_info "Raspberry Pi detected. Adding 'setup_polkit_rule' to the default steps."
  STEPS+=("setup_polkit_rule")
else
  log_info "Non-Raspberry Pi device detected. Skipping 'setup_polkit_rule' by default."
fi

USER_STEPS=()
SKIP_STEPS=()

if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
else
  SUDO=""
fi

usage() {
  cat << EOF
Usage: $0 [OPTIONS]

Options:
  -h, --help                Display this help message and exit.
  -i                        Run in interactive mode (prompt before each step).
  -y                        Run in non-interactive mode (default).
  --skip-dbus               Skip dbus-related setup.
  --skip-gstreamer          Skip GStreamer installation.
  --skip-polkit             Skip adding the Polkit rule.
  --minimal                 Minimal installation (only mandatory steps).
  --system-site-packages    Enable shared system-level Python packages in the virtual environment
                            (default: enabled on Raspberry Pi, disabled otherwise).
  --no-system-site-packages Disable shared system-level Python packages in the virtual environment
                            (default: disabled on non-Raspberry Pi, enabled otherwise).
  -s STEPS                  Comma-separated list of steps to execute.
                            (Overrides default steps if provided.)
  -n STEPS                  Comma-separated list of steps to skip.
                            Available steps: install_system_deps, setup_gstreamer, create_venv,
                            install_python_deps, setup_polkit_rule.
  --dry-run                 Perform a dry run, showing commands without executing them.

Available steps:
  install_system_deps       OS-level dependencies (apt-get update, install build tools, meson, etc.)
  create_venv               Create Python virtual environment (.venv)
  install_python_deps       Install pip packages from requirements.txt
  setup_gstreamer           Install GStreamer and its OS-level dependencies
  setup_polkit_rule         Set up a Polkit rule to allow users in the 'sudo' group
                            to power off and reboot the system (useful for enabling these options
                            in the UI without requiring sudo).

Examples:
  $0                        Run all default steps in non-interactive mode.
  $0 -i                     Run interactively (prompt before each step)
  $0 --minimal              Only perform minimal installation (skip setup_gstreamer and setup_polkit_rule).
  $0 -s setup_gstreamer     Install GStreamer.
  $0 -s setup_polkit_rule   Setup polkit rule for power off and rebooting from UI.
  $0 -s create_venv,install_python_deps Create venv and install pip dependencies.
  $0 --dry-run              Perform a dry run, showing commands without executing them.
  $0 -n setup_gstreamer     Skip GStreamer installation.
EOF
  exit 0
}

run_cmd() {
  if [ "$DRY_RUN" -eq 1 ]; then
    log_info "Dry-run: $*"
  else
    log_info "Executing: $*"
    eval "$*"
  fi
}

command_exists() {
  command -v "$1" > /dev/null 2>&1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      -h | --help)
        usage
        ;;
      -i)
        INTERACTIVE="interactive"
        SKIP_PROMPT="no"
        ;;
      -y)
        INTERACTIVE="non-interactive"
        SKIP_PROMPT="yes"
        ;;
      --skip-polkit)
        SKIP_POLKIT=1
        ;;
      --skip-dbus)
        SKIP_DBUS=1
        ;;
      --skip-gstreamer)
        SKIP_GSTREAMER=1
        ;;
      --minimal)
        MINIMAL=1
        ;;
      --dry-run)
        DRY_RUN=1
        ;;
      --system-site-packages)
        SYSTEM_SITE_PACKAGES=1
        ;;
      --no-system-site-packages)
        SYSTEM_SITE_PACKAGES=0
        ;;
      -s)
        if [[ -n $2 ]]; then
          IFS=',' read -r -a USER_STEPS <<< "$2"
          STEPS=("${USER_STEPS[@]}")
          shift
        else
          log_error "-s requires a comma-separated list of steps."
          usage
        fi
        ;;
      -n)
        if [[ -n $2 ]]; then
          IFS=',' read -r -a SKIP_STEPS <<< "$2"
          shift
        else
          log_error "-n requires a comma-separated list of steps to skip."
          usage
        fi
        ;;
      *)
        log_error "Unknown option: $1"
        usage
        ;;
    esac
    shift
  done
}

install_system_deps() {
  log_info "Installing system-level dependencies..."
  run_cmd "$SUDO apt-get update"
  run_cmd "$SUDO apt-get install -y build-essential meson"
  log_info "Installing system-level dependencies for pydub..."
  run_cmd "$SUDO apt-get install -y ffmpeg libavcodec-extra"
  # for sounddevice
  run_cmd "$SUDO apt-get install -y portaudio19-dev"

  # for PyGObject
  run_cmd "$SUDO apt-get install -y cairo"

  if [[ $SKIP_DBUS -eq 0 ]]; then
    log_info "Installing dbus development libraries..."
    run_cmd "$SUDO apt-get install -y libdbus-1-dev libglib2.0-dev" || {
      log_error "Failed to install dbus-python system dependencies."
      exit 1
    }
  else
    log_info "Skipping dbus development libraries as requested."
  fi
}

create_venv() {
  if ! command_exists python3; then
    log_error "Python 3 is not installed or not in PATH. Please install it and try again."
    exit 1
  fi

  if [ -d ".venv" ]; then
    log_info "Virtual environment '.venv' already exists. Skipping creation."
  else

    if [[ -z $SYSTEM_SITE_PACKAGES ]]; then
      if is_raspberry_pi; then
        SYSTEM_SITE_PACKAGES=1
      else
        SYSTEM_SITE_PACKAGES=0
      fi
    fi

    if [[ $SYSTEM_SITE_PACKAGES -eq 1 ]]; then
      log_info "Using '--system-site-packages' for the virtual environment."
      SYSTEM_SITE_PACKAGES_FLAG="--system-site-packages"
    else
      log_info "Not using '--system-site-packages' for the virtual environment."
      SYSTEM_SITE_PACKAGES_FLAG=""
    fi

    log_info "Creating Python virtual environment in '.venv'..."
    run_cmd "python3 -m venv $SYSTEM_SITE_PACKAGES_FLAG .venv"
  fi
}

install_python_deps() {
  # shellcheck disable=SC1091
  . .venv/bin/activate

  log_info "Upgrading pip..."
  run_cmd "pip install --quiet --upgrade pip"
  log_info "Installing Python dependencies from requirements.txt..."
  run_cmd "pip install -r requirements.txt"
  run_cmd "pip install platformdirs -U --force-reinstall"

  if ! is_raspberry_pi; then
    log_info "Non-Raspberry Pi system detected. Installing dev dependencies..."
    run_cmd "pip install -r requirements-dev.txt"
  fi
}

setup_gstreamer() {
  if [[ $SKIP_GSTREAMER -eq 1 || $MINIMAL -eq 1 ]]; then
    log_info "Skipping GStreamer installation."
    return
  fi
  log_info "Installing system dependencies for GStreamer support..."

  run_cmd "$SUDO apt-get install -y python3-dev python3-numpy \
      libunwind-dev libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base \
      gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
      gstreamer1.0-libav gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl \
      gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio \
      libavcodec-dev libavformat-dev libswscale-dev \
      libgstreamer-plugins-base1.0-dev \
      libgstreamer1.0-dev libgtk-3-dev \
      libpng-dev libjpeg-dev libopenexr-dev libtiff-dev libwebp-dev \
      libopencv-dev x264 libx264-dev libssl-dev ffmpeg"

  run_cmd "$SUDO apt-get install -y python3-gi gir1.2-gstreamer-1.0"
  log_info "GStreamer is successfully installed"
}

setup_polkit_rule() {
  if [[ $SKIP_POLKIT -eq 1 ]]; then
    log_info "Skipping setup polkit rule."
    return
  fi
  if [ -f "$POLKIT_RULE_FILE" ]; then
    log_warn "Polkit rule already exists at $POLKIT_RULE_FILE. Skipping rule creation."
  else
    log_info "Creating Polkit rule at $POLKIT_RULE_FILE..."
    if [ $DRY_RUN -eq 1 ]; then
      log_info "Dry-run: Would create file $POLKIT_RULE_FILE with polkit rule contents."
    else
      cat <<- EOL | $SUDO tee "$POLKIT_RULE_FILE" > /dev/null
polkit.addRule(function(action, subject) {
    if ((action.id == "org.freedesktop.login1.power-off" || action.id == "org.freedesktop.login1.reboot") &&
        subject.isInGroup("sudo")) {
        return polkit.Result.YES;
    }
});
EOL
      log_info "Polkit rule created successfully."
    fi
  fi

  log_info "Restarting the Polkit service to apply the new rule..."
  run_cmd "systemctl restart $POLKIT_SERVICE" || {
    log_warn "Failed to restart the Polkit service. Please ensure the 'polkit' service is installed and running."
  }
  log_info "Setup completed. Users in the 'sudo' group can now reboot/shut down without interactive authorization."
}

prompt_step() {
  local step_name="$1"
  if [[ $SKIP_PROMPT == "no" ]]; then
    read -r -p "Execute step '$step_name'? [Y/n] " resp
    case "$resp" in
      [nN]*) return 1 ;;
      *) return 0 ;;
    esac
  fi
  return 0
}

execute_steps() {
  for step in "${STEPS[@]}"; do
    for s in "${SKIP_STEPS[@]}"; do
      if [[ "$step" == "$s" ]]; then
        log_info "Skipping step '$step' as specified by -n option."
        continue 2
      fi
    done
    if prompt_step "$step"; then
      log_info "Executing $step..."
      $step
    else
      log_info "Skipped step '$step' per user prompt."
    fi
  done
}

main() {
  parse_args "$@"
  log_info "Running in $INTERACTIVE mode. Dry-run mode is $([ $DRY_RUN -eq 1 ] && echo Enabled || echo Disabled)."

  if [[ $MINIMAL -eq 1 ]]; then
    log_info "Minimal installation requested; optional steps will be removed."
    NEW_STEPS=()
    for s in "${STEPS[@]}"; do
      if [[ "$s" == "setup_gstreamer" || "$s" == "setup_polkit_rule" ]]; then
        continue
      fi
      NEW_STEPS+=("$s")
    done
    STEPS=("${NEW_STEPS[@]}")
  fi

  execute_steps
  log_info "Environment setup completed successfully!"
}

main "$@"
