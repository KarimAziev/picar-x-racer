# Picar-X Racer

`Picar-X Racer` is a project aimed at controlling the [Picar-X vehicle](https://docs.sunfounder.com/projects/picar-x/en/stable/) using a modern web interface inspired by racing video games. It integrates both frontend and backend components to manage the car's movement, camera, and other functionalities. The new interface includes a speedometer, live camera feed, and multimedia controls.

![Alt text](./demo/picar-x-racer-demo.gif)

## Features

- **Real-time Control with Video Game-like Precision**: Experience smooth and responsive control over your Picar-X car, similar to a video game interface.
- **Advanced Object Detection with AI**: Integrate AI-powered [object detection modes](#object-detection) to recognize and track objects like cats, persons, and more in real-time.
- **Dynamic Video Enhancements**: Apply various [video enhancements](#video-enhancers) to your live camera feed.
- **Smooth Calibration**: Quickly switch to the [calibration mode](#calibration-mode) and adjust the settings.
- **Acceleration and Speed Indicators**: Realistic acceleration, speed indicators, and smooth driving experience make navigating through tight spaces easy.
- **Full Customization**: Change every shortcut, panel view, and more.
- **Multimedia Functionality**: Play sounds and music, and convert text to speech for interactive experiences.
- **3D Car Visualization**: A real-time 3D model of the Picar-X that reflects and displays the car's angles, providing an enhanced visual control experience.

![Alt text](./demo/3d-picar-x.gif)

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
>   - [Modes](#modes)
>     - [Object Detection](#object-detection)
>       - [Available Detection Modes](#available-detection-modes)
>       - [How to Use](#how-to-use)
>       - [Technical Details](#technical-details)
>     - [Video Enhancers](#video-enhancers)
>       - [Available Enhancement Modes](#available-enhancement-modes)
>       - [How to Use](#how-to-use-1)
>       - [Applications](#applications)
>     - [Avoid Obstacles Mode](#avoid-obstacles-mode)
>     - [Calibration Mode](#calibration-mode)
>     - [3D Virtual Mode](#3d-virtual-mode)
>   - [Development on Non-Raspberry OS](#development-on-non-raspberry-os)
>     - [Backend](#backend)
>     - [Makefile Usage](#makefile-usage)
>       - [Development Environment Setup](#development-environment-setup)
>   - [Project Status](#project-status)

<!-- markdown-toc end -->

## Prerequisites

- Python 3.11
- Node.js and npm
- make

## Raspberry OS Setup

The `bullseye` version of Raspberry Pi OS has Python 3.9 preinstalled. However, since we need Python 3.11, the easiest way to install it is with [Pyenv](https://github.com/pyenv/pyenv).

```
pyenv install 3.11
```

You can optionally make it the default:

```
pyenv global 3.11
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

| Label                             | Default Key | Description                                                                            |     |
| --------------------------------- | ----------- | -------------------------------------------------------------------------------------- | --- |
| Move Forward                      | w           | Accelerates the car forward.                                                           |     |
| Move Backward                     | s           | Accelerates the car backward.                                                          |     |
| Move Left                         | a           | Turns the car left.                                                                    |     |
| Move Right                        | d           | Turns the car right.                                                                   |     |
| Stop                              | Space       | Stops the car.                                                                         |     |
| Camera Left                       | ArrowLeft   | Pans the camera to the left.                                                           |     |
| Camera Down                       | ArrowDown   | Tilts the camera downward.                                                             |     |
| Camera Right                      | ArrowRight  | Pans the camera to the right.                                                          |     |
| Camera Up                         | ArrowUp     | Tilts the camera upward.                                                               |     |
| Decrease Max Speed                | -           | Decreases the car's maximum speed.                                                     |     |
| Increase Max Speed                | =           | Increases the car's maximum speed.                                                     |     |
| Measure Distance                  | u           | Measures the distance to obstacles.                                                    |     |
| Play Music                        | m           | Plays music.                                                                           |     |
| Play Next Music Track             | 2           | Plays the next music track.                                                            |     |
| Play Previous Music Track         | 1           | Plays the previous music track.                                                        |     |
| Play Sound                        | o           | Plays a sound.                                                                         |     |
| Reset Camera Orientation          | 0           | Resets the camera's pan and tilt to the default orientation.                           |     |
| Say Text                          | k           | Speaks a predefined text.                                                              |     |
| Next Text                         | 4           | Selects the next saved text for speech without speaking.                               |     |
| Previous Text                     | 3           | Selects the previous saved text for speech without speaking.                           |     |
| Take Photo                        | t           | Captures a photo using the camera.                                                     |     |
| Next Enhance Mode                 | e           | Cycles to the next video enhancement mode. [See details](#video-enhancers)             |     |
| Previous Enhance Mode             | E           | Cycles to the previous video enhancement mode. [See details](#video-enhancers)         |     |
| Next Detect Mode                  | r           | Cycles to the next AI detection mode. [See details](#object-detection)                 |     |
| Previous Detect Mode              | R           | Cycles to the previous AI detection mode. [See details](#object-detection)             |     |
| Show Battery Voltage              | b           | Displays the current battery voltage.                                                  |     |
| Toggle Fullscreen                 | f           | Enters or exits full-screen mode.                                                      |     |
| Open Shortcuts Settings           | ?           | Opens the settings menu for keyboard shortcuts.                                        |     |
| Open General Settings             | h           | Opens the general settings menu.                                                       |     |
| Increase Video Quality            | .           | Increases the video quality.                                                           |     |
| Decrease Video Quality            | ,           | Decreases the video quality.                                                           |     |
| Increase Video Quality            | PageUp      | Increases the video quality.                                                           |     |
| Decrease Video Quality            | PageDown    | Decreases the video quality.                                                           |     |
| Toggle Speedometer View           | N           | Toggles the speedometer display on or off.                                             |     |
| Toggle 3D Car View                | M           | Toggles the 3D view of the car on or off.                                              |     |
| Toggle Text Info                  | I           | Toggles text information on or off.                                                    |     |
| Toggle Calibration Mode           | C           | Toggles calibration mode. [See details](#calibration-mode)                             |     |
| Toggle Auto Downloading Photo     | P           | Toggles automatic downloading of captured photos.                                      |     |
| Toggle 3D Virtual Mode            | \*          | Activates virtual mode. [See details](#3d-virtual-mode)                                |     |
| Toggle Auto Measure Distance Mode | U           | Toggles automatic distance measurement.                                                |     |
| Increase FPS                      | F           | Increases the frames per second.                                                       |     |
| Decrease FPS                      | S           | Decreases the frames per second.                                                       |     |
| Increase Dimension                | ]           | Increases the display dimensions.                                                      |     |
| Decrease Dimension                | [           | Decreases the display dimensions.                                                      |     |
| Increase Volume                   | PageUp      | Increases the audio volume.                                                            |     |
| Decrease Volume                   | PageDown    | Decreases the audio volume.                                                            |     |
| Toggle Avoid Obstacles Mode       | O           | Toggles a mode to automatically avoid obstacles. [See details](#avoid-obstacles-mode). |     |

## Modes

### Object Detection

![Alt text](./demo/object-detection.png)

Leverage AI-powered object detection modes to enhance your driving and monitoring experience. The Picar-X Racer integrates object detection capabilities using machine learning models to identify and track specific objects in real-time.

#### Available Detection Modes

- **None**: Detection is disabled. The car streams the standard video feed without any overlays.
- **All**: Detects all objects recognized by the AI model and overlays bounding boxes with labels.
- **Person**: Specifically detects human figures and tracks them.
- **Cat**: Specifically detects cats and tracks them.

#### How to Use

- **Switch Detection Modes**: Use the keybindings `r` (Next Detect Mode) and `R` (Previous Detect Mode) to cycle through the available detection modes.
- **Overlay Information**: When a detection mode is active, the live video feed will display bounding boxes and labels around the detected objects.
- **Applications**: Use object detection to avoid obstacles, follow subjects, or gather data about the environment.

#### Technical Details

- **AI Model**: The object detection feature utilizes the YOLOv5n model, optimized for real-time processing on devices like the Raspberry Pi.
- **Customization**: You can adjust the detection confidence threshold and customize detection parameters in the settings.

### Video Enhancers

Enhance your video streaming experience with real-time video enhancement modes.

#### Available Enhancement Modes

- **None**: No enhancement is applied. The standard video feed is displayed.
- **RoboCop Vision**: Simulates the visual effects seen in the RoboCop movies, including grayscale conversion, edge detection, scan lines, targeting reticles, and a heads-up display (HUD) overlay.
- **Predator Vision**: Simulates the thermal vision effect from the Predator movies, applying a thermal color map to highlight heat signatures.
- **Infrared Vision**: Highlights warmer areas in the image to simulate infrared imaging, useful for detecting heat sources.
- **Ultrasonic Vision**: Creates a monochromatic sonar effect by applying edge detection and a bone color map, simulating ultrasonic imaging.

#### How to Use

- **Switch Enhancement Modes**: Use the keybindings `e` (Next Enhance Mode) and `E` (Previous Enhance Mode) to cycle through the available video enhancer modes.
- **Real-time Application**: Enhancements are applied in real-time to the live video feed, providing immediate visual feedback.
- **Customization**: Some enhancement modes may have adjustable parameters for finer control, which can be configured in the settings panel.

#### Applications

- **Improved Visibility**: Enhance video feed visibility in low-light conditions or high-contrast environments.
- **Edge Detection for Navigation**: Use edge detection modes to assist with navigation and obstacle avoidance.
- **Educational and Research**: Experiment with different image processing techniques for educational purposes or computer vision research.

### Avoid Obstacles Mode

Activates a mode where the car automatically adjusts its movements to avoid obstacles based on distance measurements from a sensor.

### Calibration Mode

Activates a mode for calibration. In this mode, you can adjust the angle for servo direction, camera pan, and camera tilt. Some commands are remapped:

| Original Command Label   | Original Key | New Command Label         | New Command Description                                  |
| ------------------------ | ------------ | ------------------------- | -------------------------------------------------------- |
| Move Left                | a            | Decrease Servo Direction  | Decreases the calibration angle for the servo direction. |
| Move Right               | d            | Increase Servo Direction  | Increases the calibration angle for the servo direction. |
| Camera Down              | ArrowDown    | Decrease Camera Tilt Cali | Decreases the calibration angle for the camera's tilt.   |
| Camera Up                | ArrowUp      | Increase Camera Tilt Cali | Increases the calibration angle for the camera's tilt.   |
| Camera Left              | ArrowLeft    | Decrease Camera Pan Cali  | Decreases the calibration angle for the camera's pan.    |
| Camera Right             | ArrowRight   | Increase Camera Pan Cali  | Increases the calibration angle for the camera's pan.    |
| Reset Camera Orientation | 0            | Reset Calibration         | Resets all calibration settings.                         |

### 3D Virtual Mode

![Alt text](./demo/3D-mode-demo.png)

Hides a video stream view and focuses on controlling the car using just a 3D model visualization.
The mode is supposed to be used with active Auto Measure Distance Mode, which activates the ultrasonic measurement, and the 3D visualization will visualize the ultrasonic distance.

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
