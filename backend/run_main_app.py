from typing import Union

import uvicorn


def start_main_app(port: Union[str, int], log_level: str):

    uvicorn_config = {
        "app": "app.main_server:app",
        "host": "0.0.0.0",
        "port": int(port) if isinstance(port, str) else port,
        "log_level": log_level.lower(),
    }

    uvicorn.run(**uvicorn_config)


def main():
    import multiprocessing as mp

    try:
        mp.set_start_method("spawn")
    except RuntimeError:
        pass

    from app.core.logger import Logger
    from app.util.setup_env import setup_env

    (
        px_main_app_port,
        px_control_app_port,
        px_log_level,
        px_app_mode,
        px_frontend_port,
    ) = setup_env()
    Logger.setup_from_env()
    start_main_app(port=px_main_app_port, log_level=px_log_level)


if __name__ == "__main__":
    main()
