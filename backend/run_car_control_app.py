from typing import Union

import uvicorn


def start_control_app(port: Union[str, int], log_level: str):
    uvicorn_config = {
        "app": "app.control_server:app",
        "host": "0.0.0.0",
        "port": port if isinstance(port, int) else int(port),
        "log_level": log_level.lower(),
    }

    uvicorn.run(**uvicorn_config)


def main():
    import multiprocessing as mp

    try:
        mp.set_start_method("spawn")
    except RuntimeError:
        pass
    from robot_hat import reset_mcu_sync

    from app.util.logger import Logger
    from app.util.setup_env import setup_env

    (
        px_main_app_port,
        px_control_app_port,
        px_log_level,
        px_app_mode,
        px_frontend_port,
    ) = setup_env()

    reset_mcu_sync()
    start_control_app(port=px_control_app_port, log_level=px_log_level)

    Logger.setup_from_env()
    start_control_app(port=px_main_app_port, log_level=px_log_level)


if __name__ == "__main__":
    main()
