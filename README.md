# Picar-X Racer

`Picar-X Racer` is a project aimed at controlling the [Picar-X vehicle](https://docs.sunfounder.com/projects/picar-x/en/stable/) using a modern web interface inspired by racing video games. It integrates both frontend and backend components to manage the car's movement, camera, and other functionalities. The new interface includes a speedometer, live camera feed, and multimedia controls.

![Alt text](./picar-x-demo.gif)

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
>   - [Usage on Raspberry OS](#usage-on-raspberry-os)
>     - [Setup and Build](#setup-and-build)
>     - [Usage](#usage)
>   - [Settings Panel](#settings-panel)
>   - [Keybindings](#keybindings)
>     - [Move](#move)
>     - [Camera](#camera)
>     - [Sound Controls](#sound-controls)
>   - [Development on non-Raspberry OS](#development-on-non-raspberry-os)
>     - [Backend](#backend)
>     - [Frontend](#frontend)
>   - [Project Status](#project-status)

<!-- markdown-toc end -->

## Prerequisites

- Python 3.x
- Node.js and npm
- Raspberry PI with Picar-X

## Usage on Raspberry OS

### Setup and Build

To run on Raspberry OS, follow these steps:

1. Install [all the modules](https://docs.sunfounder.com/projects/picar-x/en/latest/python/python_start/install_all_modules.html) required by Picar-X.

2. Clone this repository to your Raspberry Pi:

```bash
git clone https://github.com/KarimAziev/picar-x-racer.git ~/picar-x-racer/
```

3. Install dependencies. Use the same Python environment as you used for the Picar-X installation. Assuming you installed it using `sudo python3`, as mentioned in the Picar-X manual:

```bash
cd ~/picar-x-racer/
sudo python3 -m pip install -r ./requirements.txt
```

4. Install [SoX](https://sourceforge.net/projects/sox/) with MP3 support. It is needed for Google Speech.

```bash
sudo apt-get install sox libsox-fmt-mp3
```

5. Build the frontend:

```bash
cd ~/picar-x-racer/frontend/
npm install
npm run build
```

### Usage

Run the script to start the server:

```bash
sudo python3 ~/picar-x-racer/backend/run.py
```

Once the application is running, open your browser and navigate to (replace `<your-raspberry-pi-ip>` with the actual IP):

```
http://<your-raspberry-pi-ip>:9000
```

After navigating to the control interface, you can customize your experience via the comprehensive settings panel:

## Settings Panel

- **Text-to-Speech**: Configure the default text that will be converted into speech.
- **Default Sound**: Select a default sound from the available list to play during specific events.
- **Sounds**: Upload new sound files and manage existing ones.
- **Default Music**: Choose default background music from the available list.
- **Music**: Upload new music files and manage existing ones.
- **Photos**: Manage and download photos captured by the Picar-X camera.

The settings panel is user-friendly, allowing for quick adjustments and uploads directly from your browser to tailor the Picar-X experience to your preference.

## Keybindings

In the browser, you can control your Picar-x with the following keys.

### Move

| Key     | Action     |
| ------- | ---------- |
| `w`     | Move Up    |
| `a`     | Move Left  |
| `d`     | Move Right |
| `s`     | Move Down  |
| `=`     | Speed Up   |
| `-`     | Speed Down |
| `Space` | Stop       |

### Camera

| Key           | Action            |
| ------------- | ----------------- |
| `Arrow Up`    | Move Camera Up    |
| `Arrow Left`  | Move Camera Left  |
| `Arrow Right` | Move Camera Right |
| `Arrow Down`  | Move Camera Down  |
| `t`           | Take Photo        |

### Sound Controls

| Key | Action          |
| --- | --------------- |
| `r` | Play sound      |
| `m` | Play/Stop Music |
| `k` | Speech          |

## Development on non-Raspberry OS

### Backend

For development outside of Raspberry Pi, you may want to set up a virtual environment to get IDE features and avoid polluting the system with global packages.

Run the following command to set up your environment. It will create a virtual environment, clone, and install `robot-hat` in a special way:

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

## Project Status

This project is a work in progress. New features and improvements are being continuously added.
