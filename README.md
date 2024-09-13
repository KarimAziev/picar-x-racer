# Picar-X Racer

`Picar-X Racer` is a project aimed at controlling the [Picar-X vehicle](https://docs.sunfounder.com/projects/picar-x/en/stable/) using a modern web interface inspired by racing video games. It integrates both frontend and backend components to manage the car's movement, camera, and other functionalities. The new interface includes a speedometer, live camera feed, and multimedia controls.

![Alt text](./picar-x-racer.gif)

## Features

- **Real-time Control with Video Game-like Precision**: Experience smooth and responsive control over your Picar-X car, similar to a video game interface.
- **Smooth Calibration**: Quickly switch to the calibration mode and adjust the settings.
- **Acceleration and Speed Indicators**: Realistic acceleration, speed indicators, and smooth driving experience make navigating through tight spaces easy.
- **3D Car Visualization**: A real-time 3D model of the Picar-X that reflects and displays the car's angles, providing an enhanced visual control experience.
- **Full Customization**: Change every shortcut, panel view, and more.
- **Multimedia Functionality**: Play sounds and music, and convert text to speech for interactive experiences.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->

**Table of Contents**

> - [Picar-X Racer](#picar-x-racer)
>   - [Features](#features)
>   - [Prerequisites](#prerequisites)
>   - [Raspberry OS Setup](#raspberry-os-setup)
>     - [Installation](#installation)
>     - [Usage](#usage)
>   - [Settings](#settings)
>     - [Default Keybindings](#default-keybindings)
>     - [Avoid Obstacles Mode](#avoid-obstacles-mode)
>   - [Development on Non-Raspberry OS](#development-on-non-raspberry-os)
>     - [Backend](#backend)
>     - [Makefile Usage](#makefile-usage)
>       - [Development Environment Setup](#development-environment-setup)
>   - [Project Status](#project-status)

<!-- markdown-toc end -->

## Prerequisites

- Python 3.10
- Node.js and npm
- make

## Raspberry OS Setup

The `bullseye` version of Raspberry Pi OS has Python 3.9 preinstalled. However, since we need Python 3.10, the easiest way to install it is with [Pyenv](https://github.com/pyenv/pyenv).

```
pyenv install 3.10
```

You can optionally make it the default:

```
pyenv global 3.10
```

This project uses neither `Picamera` nor `Picamera 2`; instead, it uses `cv2`. To access the camera, you need to edit a configuration file in the boot partition of the Raspberry Pi. If you are using the `bullseye` version of Raspberry Pi OS, it is located at `/boot/config.txt`. If you are using the `bookworm` version, it is at `/boot/firmware/config.txt`.

In this file, you need to add the following lines:

```
# Disable the automatic detection of the camera
camera_auto_detect=0

# Enable the camera
start_x=1

# Set GPU memory allocation (in megabytes)
gpu_mem=128

# Enable the VC4 graphics driver for KMS (Kernel Mode Setting)
dtoverlay=vc4-kms-v3d
```

By default, the config file contains the line `camera_auto_detect=1`. Either comment it out or replace it with `camera_auto_detect=0`.

> [!WARNING]
> These settings will make `libcamera-hello` unusable.

Next, to make building and running the project easier, you should install `make` if you don't have it already:

```bash
sudo apt install make
```

### Installation

1. Clone this repository to your Raspberry Pi:

```bash
git clone https://github.com/KarimAziev/picar-x-racer.git ~/picar-x-racer/
```

2. Go to the project directory:

```bash
cd ~/picar-x-racer/
```

3. Install dependencies and build the project in a virtual environment:

```bash
make all
```

That's all. This is a one-time setup. You can then run the project by running the following command in the project directory:

```bash
make backend-venv-run
```

### Usage

In the project root directory, run the script to start the server:

```bash
make backend-venv-run
```

Once the application is running, open your browser and navigate to (replace `<your-raspberry-pi-ip>` with the actual IP):

```
http://<your-raspberry-pi-ip>:9000
```

After navigating to the control interface, you can customize your experience via the comprehensive settings panel.

## Settings

To access settings, press the icon in the top right corner, or press `h` to open the general settings, or `?` to open keybindings settings.

![Alt text](./demo/settings-general.png)

- **Text-to-Speech**: Configure the default text that will be converted into speech.
- **Default Sound**: Select a default sound from the available list to play during specific events.
- **Sounds**: Upload new sound files and manage existing ones.
- **Default Music**: Choose default background music from the available list.
- **Music**: Upload new music files and manage existing ones.
- **Photos**: Manage and download photos captured by the Picar-X camera.
- **Keybindings**: Change all keybindings.
- **Calibration**: Start calibration mode.

![Alt text](./demo/keybindings-settings.png)

### Default Keybindings

In the browser, you can control your Picar-X with the following keys (all the keys can be changed in the settings).

| Label                         | Default Key | Description                                                     |
| ----------------------------- | ----------- | --------------------------------------------------------------- |
| Move Forward                  | w           | Accelerates the car forward.                                    |
| Move Backward                 | s           | Accelerates the car backward.                                   |
| Move Left                     | a           | Turns the car left.                                             |
| Move Right                    | d           | Turns the car right.                                            |
| Stop                          | Space       | Stops the car.                                                  |
| Camera Left                   | ArrowLeft   | Pans the camera to the left.                                    |
| Camera Down                   | ArrowDown   | Tilts the camera downward.                                      |
| Camera Right                  | ArrowRight  | Pans the camera to the right.                                   |
| Camera Up                     | ArrowUp     | Tilts the camera upward.                                        |
| Decrease Max Speed            | -           | Decreases the car's maximum speed.                              |
| Increase Max Speed            | =           | Increases the car's maximum speed.                              |
| Measure Distance              | u           | Measures the distance to obstacles.                             |
| Play Music                    | m           | Plays music.                                                    |
| Play Sound                    | o           | Plays a sound.                                                  |
| Reset Camera Orientation      | 0           | Resets the camera's pan and tilt to the default orientation.    |
| Say Text                      | k           | Speaks a predefined text.                                       |
| Take Photo                    | t           | Captures a photo using the camera.                              |
| Show Battery Voltage          | b           | Displays the current battery voltage.                           |
| Toggle Fullscreen             | f           | Enters or exits full-screen mode.                               |
| Open Shortcuts Settings       | ?           | Opens the settings menu for keyboard shortcuts.                 |
| Open General Settings         | h           | Opens the general settings menu.                                |
| Increase Video Quality        | .           | Increases the video quality.                                    |
| Decrease Video Quality        | ,           | Decreases the video quality.                                    |
| Increase Video Quality        | PageUp      | Increases the video quality.                                    |
| Decrease Video Quality        | PageDown    | Decreases the video quality.                                    |
| Toggle Speedometer View       | N           | Toggles the speedometer display on or off.                      |
| Toggle 3D Car View            | M           | Toggles the 3D view of the car on or off.                       |
| Toggle Text Info              | I           | Toggles text information on or off.                             |
| Toggle Calibration Mode       | C           | Activates calibration mode.                                     |
| Toggle Auto Downloading Photo | P           | Toggles automatic downloading of captured photos.               |
| Toggle Avoid Obstacles Mode   | O           | Activates a special mode. [See details](#avoid-obstacles-mode). |

### Avoid Obstacles Mode

Activates a mode where the car automatically adjusts its movements to avoid obstacles based on distance measurements from a sensor.

## Development on Non-Raspberry OS

For running the server in watch mode (reload on file save), we use `nodemon`, which can be installed globally with `npm`:

```bash
npm i -g nodemon
```

### Backend

To install dependencies and run the project in development mode:

```bash
make dev-with-install
```

To run the project without installing dependencies:

```bash
make dev
```

### Makefile Usage

You can also use the `Makefile` to manage various setup and development tasks more efficiently. Below are some of the make targets available:

#### Development Environment Setup

- **Setup and Run Development Environment**: Install dependencies and run the development environment.

```bash
make dev-with-install
```

- **Run Development Environment without Installing Dependencies**:

```bash
make dev-without-install
```

- **Run Frontend Development Server**:

```bash
make frontend-dev
```

- **Run Backend Development Server**:

```bash
make backend-dev-run
```

## Project Status

This project is a work in progress. New features and improvements are being continuously added.
