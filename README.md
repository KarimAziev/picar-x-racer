# Picar-X Racer

`Picar-X Racer` is a project aimed at controlling the [Picar-X vehicle](https://docs.sunfounder.com/projects/picar-x/en/stable/) using a modern web interface inspired by racing video games. It integrates both frontend and backend components to manage the car's movement, camera, and other functionalities. The new interface includes a speedometer, live camera feed, and multimedia controls.

![Alt text](./picar-x-racer.gif)

## Features

- **Real-time Control with Video Game-like Precision**: Experience smooth and responsive control over your Picar-X car, similar to a video game interface.
- **Acceleration and Speed Indicators**: Realistic acceleration, speed indicators, and smooth driving experience make navigating through tight spaces easy.
- **Web-based Interface**: Control your Picar-X directly from your browser with an integrated live video feed and intuitive controls.
- **Camera Handling**: Adjust the camera pan and tilt angles in real-time, and capture photos with a key press.
- **Keybinding Feedback**: Visual feedback for key presses to enhance the control experience.
- **Multimedia Functionality**: Play sounds and music, and convert text-to-speech for interactive experiences.
- **3D Car Visualization**: A real-time 3D model of the Picar-X that reflects and displays the car's angles, providing an enhanced visual control experience.
- **Comprehensive Settings Panel**: Manage text-to-speech, sound, music, and image settings seamlessly.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->

**Table of Contents**

> - [Picar-X Racer](#picar-x-racer)
>   - [Features](#features)
>   - [Prerequisites](#prerequisites)
>   - [Usage on Bookworm OS](#usage-on-bookworm-os)
>   - [Usage on Raspberry OS](#usage-on-raspberry-os)
>     - [Setup and Build](#setup-and-build)
>     - [Usage](#usage)
>   - [Settings](#settings)
>     - [Default Keybindings](#default-keybindings)
>     - [Avoid Obstacles Mode](#avoid-obstacles-mode)
>   - [Development on non-Raspberry OS](#development-on-non-raspberry-os)
>     - [Backend](#backend)
>     - [Frontend](#frontend)
>     - [Makefile Usage](#makefile-usage)
>       - [Development Environment Setup](#development-environment-setup)
>       - [Production Environment Setup](#production-environment-setup)
>       - [Cleanup Targets](#cleanup-targets)
>   - [Project Status](#project-status)

<!-- markdown-toc end -->

## Prerequisites

- Python 3.x
- Node.js and npm
- Raspberry PI with Picar-X

## Usage on Bookworm OS

In order to use `cv2` on `Bookworm`, you need to add the following lines in `/boot/firmware/config.txt`

```
camera_auto_detect=0
start_x=1
gpu_mem=128
dtoverlay=vc4-kms-v3d
```

## Usage on Raspberry OS

### Setup and Build

To run on Raspberry OS, follow these steps:

1. Install `portaudio19-dev` required by Pyaudio.

```bash
sudo apt-get install portaudio19-dev
```

2. Install [SoX](https://sourceforge.net/projects/sox/) with MP3 support. It is needed for Google Speech.

```bash
sudo apt-get install sox libsox-fmt-mp3
```

3. Clone this repository to your Raspberry Pi:

```bash
git clone https://github.com/KarimAziev/picar-x-racer.git ~/picar-x-racer/
```

4. Install backend dependencies. Use the same Python environment as you used for the Picar-X installation. Assuming you installed it using `sudo python3`, as mentioned in the Picar-X manual:

```bash
cd ~/picar-x-racer/backend/
sudo python3 -m pip install -r ./requirements.txt
```

5. Build the frontend:

```bash
cd ~/picar-x-racer/frontend/
npm install
npm run build
```

### Usage

Run the script to start the server. Use the same Python environment as you used for the Picar-X installation. Assuming you installed it using `sudo python3`, as mentioned in the Picar-X manual:

```bash
sudo python3 ~/picar-x-racer/backend/run.py
```

Once the application is running, open your browser and navigate to (replace `<your-raspberry-pi-ip>` with the actual IP):

```
http://<your-raspberry-pi-ip>:9000
```

After navigating to the control interface, you can customize your experience via the comprehensive settings panel:

## Settings

To access settings press the icon in the right top corner, or press `h` to open the general settings, or `?` - to open keybindings settings.

![Alt text](./demo/settings-general.png)

- **Text-to-Speech**: Configure the default text that will be converted into speech.
- **Default Sound**: Select a default sound from the available list to play during specific events.
- **Sounds**: Upload new sound files and manage existing ones.
- **Default Music**: Choose default background music from the available list.
- **Music**: Upload new music files and manage existing ones.
- **Photos**: Manage and download photos captured by the Picar-X camera.
- **Keybindings**: You can change all key bindings.

![Alt text](./demo/keybindings-settings.png)

### Default Keybindings

In the browser, you can control your Picar-X with the following keys (all the keys can be changed in the settings).

| Label                       | Default Key | Description                                                     |
| --------------------------- | ----------- | --------------------------------------------------------------- |
| Move Forward                | w           | Accelerates the car forward.                                    |
| Move Backward               | s           | Accelerates the car backward.                                   |
| Move Left                   | a           | Turns the car left.                                             |
| Move Right                  | d           | Turns the car right.                                            |
| Stop                        | Space       | Stops the car.                                                  |
| Camera Left                 | ArrowLeft   | Pans the camera to the left.                                    |
| Camera Down                 | ArrowDown   | Tilts the camera downward.                                      |
| Camera Right                | ArrowRight  | Pans the camera to the right.                                   |
| Camera Up                   | ArrowUp     | Tilts the camera upward.                                        |
| Decrease Max Speed          | -           | Decreases the car's maximum speed.                              |
| Increase Max Speed          | =           | Increases the car's maximum speed.                              |
| Measure Distance            | u           | Measures the distance to obstacles.                             |
| Play Music                  | m           | Plays music.                                                    |
| Play Sound                  | o           | Plays a sound.                                                  |
| Reset Camera Orientation    | 0           | Resets the camera's pan and tilt to default orientation.        |
| Say Text                    | k           | Speaks out a predefined text.                                   |
| Take Photo                  | t           | Captures a photo using the camera.                              |
| Show Battery Voltage        | b           | Displays the current battery voltage.                           |
| Toggle Fullscreen           | f           | Enters or exits full-screen mode.                               |
| Open Shortcuts Settings     | ?           | Opens the settings menu for keyboard shortcuts.                 |
| Open General Settings       | h           | Opens the general settings menu.                                |
| Increase Video Quality      | .           | Increases the video quality.                                    |
| Increase Video Quality      | PageUp      | Increases the video quality.                                    |
| Decrease Video Quality      | ,           | Decreases the video quality.                                    |
| Decrease Video Quality      | PageDown    | Decreases the video quality.                                    |
| Toggle Speedometer View     | N           | Toggles the speedometer display on or off.                      |
| Toggle 3D Car View          | M           | Toggles the 3D view of the car on or off.                       |
| Toggle Text Info            | I           | Toggles text information on or off.                             |
| Toggle FPS Drawing          | F           | Turns the FPS display on or off.                                |
| Toggle Avoid Obstacles Mode | O           | Activates a special mode. [See details](#avoid-obstacles-mode). |

### Avoid Obstacles Mode

Activates a mode where the car automatically adjusts its movements to avoid obstacles based on distance measurements from a sensor.

## Development on non-Raspberry OS

### Backend

For development outside of Raspberry Pi, you may want to set up a virtual environment to get IDE features and avoid polluting the system with global packages.

Run the following command to set up your environment. It will create a virtual environment, clone, and install `robot-hat` in a special way:

```bash
cd ./backend
```

```bash
./setup_env.sh
```

This script checks whether you are on Raspbian OS. If not, it sets up a virtual environment and installs the necessary dependencies.

### Frontend

Navigate to the frontend directory:

```bash
cd ./frontend
```

Install dependencies:

```bash
npm install
```

Run the application:

```bash
npm run dev
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

#### Production Environment Setup

- **Install and Build Both Frontend and Backend (Development)**:

```bash
make build-dev-all
```

- **Install and Build Both Frontend and Backend (Production)**:

```bash
make sudo-build-all
```

- **Run Backend in Production Mode**:

```bash
make backend-sudo-run
```

- **Install Backend Dependencies (Production)**:

```bash
make backend-sudo-install
```

#### Cleanup Targets

- **Clean All Build Artifacts**:

```bash
make clean
```

- **Clean Python Bytecode Files**:

```bash
make clean-pyc
```

- **Clean Frontend Build Artifacts**:

```bash
make clean-build
```

- **Display Help Message**:

```bash
make help
```

## Project Status

This project is a work in progress. New features and improvements are being continuously added.
