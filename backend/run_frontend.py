import os
import subprocess
import time
from typing import Union


def wait_for_backend_ready(signal_file_path: str, timeout: int = 60):
    """
    Waits for the backend to create a signal file indicating it is ready.

    :param signal_file_path: The path to the signal file.
    :param timeout: Maximum time to wait for the signal, in seconds.
    :return: True if the signal file is detected, False if times out.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(signal_file_path):
            print(f"Backend is ready! Proceeding to start the frontend.")
            return True
        print(
            f"Waiting for backend to be ready... ({int(time.time() - start_time)}s elapsed)"
        )
        time.sleep(1)

    print(f"Timed out waiting for the backend to be ready after {timeout} seconds.")
    return False


def start_frontend_app(
    frontend_port: Union[int, str] = 4000,
    api_port: Union[int, str] = 8000,
    ws_port: Union[int, str] = 8001,
):
    """
    Starts the frontend application using `npm run dev`, but after making sure the backend is ready.
    """
    frontend_app_directory = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "frontend"
    )

    vite_config = os.path.join(frontend_app_directory, "vite.config.ts")

    node_modules_dir = os.path.join(frontend_app_directory, "node_modules")

    vite_executable = os.path.join(node_modules_dir, ".bin", "vite")

    # Wait for the signal that the backend is ready
    signal_file_path = "/tmp/backend_ready.signal"
    if not wait_for_backend_ready(signal_file_path):
        print("Backend did not start in time. Exiting.")
        return

    env = os.environ.copy()
    env["VITE_MAIN_APP_PORT"] = str(api_port)
    env["VITE_WS_APP_PORT"] = str(ws_port)
    env["VITE_DEV_SERVER_PORT"] = str(frontend_port)

    vite_command = [vite_executable, "-c", vite_config]
    process = None

    try:
        process = subprocess.run(vite_command, cwd=frontend_app_directory, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Error starting the frontend app: {e}")
        raise
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Shutting down the frontend app...")
        if process:
            process.terminate()
