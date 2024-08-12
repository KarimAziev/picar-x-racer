# Picar-X Racer

Picar-X Racer is a project aimed at controlling the Picar-X vehicle using a web interface. It integrates both frontend and backend components to manage the car's movement, camera, and other functionalities.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->

**Table of Contents**

> - [Picar-X Racer](#picar-x-racer)
>   - [Prerequisites](#prerequisites)
>   - [Usage on Raspberry OS](#usage-on-raspberry-os)
>     - [Setup and Build](#setup-and-build)
>     - [Usage](#usage)
>   - [Development on non-Raspberry OS](#development-on-non-raspberry-os)
>     - [Backend](#backend)
>     - [Frontend](#frontend)
>   - [Project Status](#project-status)

<!-- markdown-toc end -->

## Prerequisites

- Python 3.x
- Node.js and npm

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

4. Build the frontend:

```bash
cd ~/picar-x-racer/front-end/
npm install
npm run build
```

### Usage

Run the script to start the server:

```bash
sudo python3 ~/picar-x-racer/backend/start_video_car.py
```

Once the application is running, open your browser and navigate to (replace `<your-raspberry-pi-ip>` with the actual IP):

```
http://<your-raspberry-pi-ip>:9000
```

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
cd ./front-end
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
