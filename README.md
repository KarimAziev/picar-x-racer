# Picar-X Racer

Picar-X Racer is a project to control the Picar-X vehicle using a web interface, integrating both frontend and backend components to manage the car's movement, camera, and other functionalities.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->

**Table of Contents**

> - [Picar-X Racer](#picar-x-racer)
>   - [Setup and Development](#setup-and-development)
>     - [Prerequisites](#prerequisites)
>     - [Setting Up the Environment](#setting-up-the-environment)
>     - [Installing Dependencies](#installing-dependencies)
>     - [Building the Frontend](#building-the-frontend)
>     - [Running the Application](#running-the-application)
>     - [Accessing the Frontend](#accessing-the-frontend)
>   - [Project Status](#project-status)

<!-- markdown-toc end -->

## Setup and Development

### Prerequisites

- Python 3.x
- Node.js and npm

### Setting Up the Environment

For development and running the project outside of Raspberry Pi, you need to set up the environment to mimic the robot-hat library functionalities.

Run the following command to set up your environment:

```bash
./setup_env.sh
```

This script checks whether you are on a Raspbian OS. If not, it sets up a virtual environment and installs necessary dependencies.

### Installing Dependencies

1. **Backend:**

   Ensure the virtual environment is active:

   ```bash
   source .venv/bin/activate
   ```

   Install the Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. **Frontend:**

   Navigate to the `front-end` directory and install the npm dependencies:

   ```bash
   cd front-end
   npm install
   ```

### Building the Frontend

After setting up the dependencies, you can build the frontend assets:

```bash
npm run build
```

This will generate the assets in the `front-end/dist` directory.

### Running the Application

To start the backend application on Raspberry Pi, run:

```bash
python3 backend/start_video_car.py
```

### Accessing the Frontend

Once the application is running, open your browser and navigate to:

```
http://<your-raspberry-pi-ip>:9000
```

This will load the frontend interface where you can control your Picar-X and view the live camera feed.

## Project Status

This project is a work in progress. New features and improvements are being continuously added.
