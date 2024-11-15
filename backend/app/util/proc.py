import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import multiprocessing as mp


def terminate_processes(processes: list["mp.Process"], allow_exit=False):
    COLOR_YELLOW = "\033[33m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    for process in processes:
        try:
            print(f"{BOLD}{COLOR_YELLOW}Terminating process {process.name}.{RESET}")
            process.terminate()
            print(f"{BOLD}{COLOR_YELLOW}Joining process {process.name}.{RESET}")
            process.join()
        except Exception:
            pass

    for process in processes:
        try:
            print(f"{BOLD}{COLOR_YELLOW}Closing process {process.name}.{RESET}")
            process.close()
        except (Exception, ValueError):
            pass

    if allow_exit:
        print(f"{BOLD}{COLOR_YELLOW}Processes terminated. Exiting.{RESET}")
        sys.exit(0)
