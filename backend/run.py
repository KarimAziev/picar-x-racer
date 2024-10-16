import multiprocessing as mp
import sys


def terminate_processes(processes: list[mp.Process]):
    COLOR_YELLOW = "\033[33m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    print(f"{BOLD}{COLOR_YELLOW}Terminating picar-x-racer processes...{RESET}")

    for process in processes:
        process.join()

    for process in processes:
        process.close()

    print(f"{BOLD}{COLOR_YELLOW}Child processes terminated. Exiting.{RESET}")
    sys.exit(0)


if __name__ == "__main__":
    try:
        mp.set_start_method("spawn")
    except RuntimeError:
        pass

    from app.util.logger import Logger
    from app.util.reset_mcu_sync import reset_mcu_sync
    from app.util.setup_env import setup_env
    from run_car_control_app import start_control_app
    from run_frontend import start_frontend_app
    from run_main_app import start_main_app

    setup_env()
    reset_mcu_sync()
    Logger.setup_from_env()

    px_main_app_port, px_control_app_port, px_log_level, px_app_mode = setup_env()

    main_app_process = mp.Process(
        target=start_main_app,
        args=(px_main_app_port, px_log_level, px_app_mode),
    )
    websocket_app_process = mp.Process(
        target=start_control_app,
        args=(px_control_app_port, px_log_level, px_app_mode),
    )

    processes = [main_app_process, websocket_app_process]

    if px_app_mode == "dev":
        frontend_dev_process = mp.Process(
            target=start_frontend_app,
            args=(px_main_app_port, px_control_app_port),
        )
        processes.append(frontend_dev_process)

    try:
        for proc in processes:
            proc.start()

        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Initiating graceful shutdown...")
        terminate_processes(processes)
    except Exception as e:
        print(f"An error occurred: {e}")
        terminate_processes(processes)
