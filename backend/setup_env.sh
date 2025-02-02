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

# ffmpeg is needed for pydub

install_ffmpeg_with_apt() {
  log_info "Using apt-get to install ffmpeg..."
  if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
  else
    SUDO=""
  fi
  $SUDO apt-get update
  $SUDO apt-get install -y ffmpeg libavcodec-extra
}

install_ffmpeg_with_yum() {
  log_info "Using yum to install ffmpeg..."
  if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
  else
    SUDO=""
  fi
  $SUDO yum install -y epel-release
  $SUDO yum install -y ffmpeg ffmpeg-devel
}

install_ffmpeg_with_dnf() {
  log_info "Using dnf to install ffmpeg..."
  if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
  else
    SUDO=""
  fi
  $SUDO dnf install -y ffmpeg ffmpeg-devel
}

install_ffmpeg_with_brew() {
  log_info "Using Homebrew to install ffmpeg..."
  brew install ffmpeg
}

if command_exists ffmpeg; then
  log_info "ffmpeg is already installed."
else
  log_warn "ffmpeg is not installed. Attempting to install it..."

  if command_exists apt-get; then
    install_ffmpeg_with_apt || log_warn "Failed to install ffmpeg with apt-get."
  elif command_exists yum; then
    install_ffmpeg_with_yum || log_warn "Failed to install ffmpeg with yum."
  elif command_exists dnf; then
    install_ffmpeg_with_dnf || log_warn "Failed to install ffmpeg with dnf."
  elif command_exists brew; then
    install_ffmpeg_with_brew || log_warn "Failed to install ffmpeg with Homebrew."
  else
    log_warn "No supported package manager found to install 'ffmpeg'. Continuing without it."
  fi

  if command_exists ffmpeg; then
    log_info "ffmpeg installation process completed successfully!"
  else
    log_warn "ffmpeg could not be installed. Some functionality may not work properly."
  fi
fi

if ! command_exists python3; then
  log_error "Python 3 is not installed or not in PATH. Please install it and try again."
  exit 1
fi

if [ -d ".venv" ]; then
  log_info "Virtual environment '.venv' already exists. Skipping creation."
else
  log_info "Creating Python virtual environment in '.venv'..."
  python3 -m venv --system-site-packages .venv
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
pip install -r requirements.txt

is_raspberry_pi() {
  if [ -f /proc/device-tree/model ]; then
    if grep -qi "raspberry pi" /proc/device-tree/model; then
      return 0
    fi
  fi
  return 1
}

install_dbus_python_dependencies() {
  if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
  else
    SUDO=""
  fi

  log_info "Installing system dependencies for 'dbus-python' using apt-get..."
  $SUDO apt-get update
  $SUDO apt-get install -y libdbus-1-dev libglib2.0-dev build-essential python3-dev meson || {
    log_error "Failed to install dbus-python system dependencies."
    exit 1
  }
}

compile_cv2() {
  if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
  else
    SUDO=""
  fi

  pip uninstall opencv-python -y

  log_info "Installing open-cv2 dependencies..."

  # Install essential dependencies for compiling OpenCV with desired features
  # These include tools for building software (build-essential, cmake, python3-dev)
  # and libraries for multimedia (GStreamer, FFmpeg, libav), image I/O (libpng, libjpeg, libtiff, etc.),
  # GUI functionality (libgtk-3-dev), and Python bindings (python3-numpy).
  $SUDO apt install build-essential cmake git python3-dev python3-numpy \
    libavcodec-dev libavformat-dev libswscale-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer1.0-dev libgtk-3-dev \
    libpng-dev libjpeg-dev libopenexr-dev libtiff-dev libwebp-dev \
    libopencv-dev x264 libx264-dev libssl-dev ffmpeg

  # we need this for:
  # python3 -c 'import gi; gi.require_version("Gst", "1.0"); from gi.repository import Gst; Gst.init(None); print("GStreamer version:", Gst.version())'
  $SUDO apt-get install python3-gi gir1.2-gstreamer-1.0

  log_info "Compiling open-cv2. Note, this may take a while..."

  # Reinstall OpenCV from source, instead of using pre-built binaries
  # The `--no-binary opencv-python` forcibly disables downloading pre-built packages from PyPI
  # and forces compiling OpenCV from source with system-level dependencies.
  # This ensures GStreamer and other optional functionalities will be included if their dependencies are available.
  python -m pip install --no-binary opencv-python opencv-python
  log_info "open-cv2 is installed and compiled."
}

if is_raspberry_pi; then
  log_info "Raspberry Pi detected. Installing system-level dependencies for 'dbus-python'..."
  install_dbus_python_dependencies
  compile_cv2
  log_info "Raspberry Pi detected. Standard installation complete."
else
  log_info "Non-Raspberry Pi system detected. Setting up IDE environment..."
  if [ ! -f "requirements-dev.txt" ]; then
    log_error "requirements-dev.txt file not found. Please ensure it exists in the current directory."
    exit 1
  fi
  log_info "Installing development dependencies from requirements-dev.txt..."
  pip install -r requirements-dev.txt
  compile_cv2
  log_info "IDE environment setup completed."
fi

log_info "Setup completed successfully!"
