import os
from typing import Union

import uvicorn


def start_control_app(port: Union[str, int], log_level: str, mode: str):
    app_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "app")
    uvicorn_config = {
        "app": "app.control_server:app",
        "host": "0.0.0.0",
        "port": port if isinstance(port, int) else int(port),
        "log_level": log_level.lower(),
    }

    if mode == "dev":
        uvicorn_config.update(
            {
                "reload": True,
                "reload_includes": ["*.py"],
                "reload_dirs": [app_directory],
                "reload_excludes": ["*.log", "tmp/*"],
            }
        )

    uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    from app.util.reset_mcu_sync import reset_mcu_sync
    from app.util.setup_env import setup_env

    px_main_app_port, px_control_app_port, px_log_level, px_app_mode = setup_env()

    reset_mcu_sync()
    start_control_app(
        port=px_control_app_port, log_level=px_log_level, mode=px_app_mode
    )
