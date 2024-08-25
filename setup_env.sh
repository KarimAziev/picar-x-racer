#!/bin/bash

# Check if the OS is Raspbian
if ! grep -q "Raspbian" /etc/os-release; then
  echo "This is not a Raspbian OS. Setting up IDE environment..."

  # Create and activate a virtual environment
  python3 -m venv .venv
  source .venv/bin/activate

  pip install --upgrade pip
  # Clone the robot-hat repository
  if [ ! -d "./robot-hat" ]; then
    echo "Cloning robot hat"
    git clone -b v2.0 https://github.com/sunfounder/robot-hat.git
    # shellcheck disable=SC2164

    # Override setup.py
    # The original `setup.py` script in the robot-hat repository includes
    # additional logic for handling Raspbian-specific dependencies,
    # configurations, and commands that are not applicable or necessary in a
    # general development environment.
    #
    # Overriding the script simplifies installation by removing these additional
    # steps, making it more straightforward and less error-prone for non-Raspbian
    # systems.
    cat << EOF > ./robot-hat/setup.py
from setuptools import setup, find_packages
import sys

sys.path.append("./robot_hat")

try:
    from version import __version__  # type: ignore
except ImportError:
    __version__ = None

setup(
    name="robot_hat",
    version=__version__ if __version__ else "1.0.0",
    description="Library for SunFounder Robot Hat",
    url="https://github.com/sunfounder/robot-hat/tree/v2.0",
    author="SunFounder",
    author_email="service@sunfounder.com",
    license="GNU",
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python :: 3",
    ],
    keywords="python raspberry pi GPIO sunfounder",
    packages=find_packages(exclude=["tests", "docs"]),
)
EOF

    # Install the modified package
    pip install ./robot-hat --force-reinstall
  fi

  # Return to the scripts directory
  echo "Installing dependencies."
  pip install -r requirements.txt
  echo "Installing dev dependencies."
  pip install -r requirements-dev.txt
  echo "IDE environment setup completed."
else
  echo "This is a Raspbian OS. Standard installation will proceed."

fi
