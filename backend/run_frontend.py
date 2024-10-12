import os
import subprocess
import time


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


def start_frontend_app(port: int = 8000, ws_port: int = 8001):
    """
    Starts the frontend application using `npm run dev`, but after making sure the backend is ready.
    """
    frontend_app_directory = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "frontend"
    )

    os.chdir(frontend_app_directory)

    # Wait for the signal that the backend is ready
    signal_file_path = '/tmp/backend_ready.signal'
    if not wait_for_backend_ready(signal_file_path):
        print("Backend did not start in time. Exiting.")
        return

    env = os.environ.copy()
    env["VITE_MAIN_APP_PORT"] = str(port)
    env["VITE_WS_APP_PORT"] = str(ws_port)

    npm_command = ["npm", "run", "dev"]
    process = None

    try:
        process = subprocess.run(npm_command, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Error starting the frontend app: {e}")
        raise
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Shutting down the frontend app...")
        if process:
            process.terminate()
