import sys
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    import multiprocessing as mp


def terminate_processes(processes: List[Optional["mp.Process"]], allow_exit=False):
    """
    Gracefully terminates a list of multiprocessing processes.

    Optionally, the function can exit the current program after termination is complete.

    Args:
    - processes: A list of multiprocessing processes to terminate.
    - allow_exit: If True, exits the program after all processes are terminated, joined, and closed.
    """
    COLOR_YELLOW = "\033[33m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    for process in processes:
        if process is None:
            continue
        try:
            print(f"{BOLD}{COLOR_YELLOW}Terminating process {process.name}.{RESET}")
            process.terminate()

        except Exception:
            pass

    for process in processes:
        if process is None:
            continue
        try:
            print(f"{BOLD}{COLOR_YELLOW}Joining process {process.name}.{RESET}")
            process.join(10)
            print(f"{BOLD}{COLOR_YELLOW}Joined process {process.name}.{RESET}")

            if process.is_alive():
                print(
                    f"{BOLD}{COLOR_YELLOW}Process {process.name} still alive. Terminating. {RESET}"
                )
                process.terminate()
                print(f"{BOLD}{COLOR_YELLOW}Joining {process.name}. {RESET}")
                process.join(5)

        except Exception:
            pass

    for process in processes:
        if process is None:
            continue
        try:
            print(f"{BOLD}{COLOR_YELLOW}Closing process {process.name}.{RESET}")
            process.close()
        except (Exception, ValueError):
            pass

    if allow_exit:
        print(f"{BOLD}{COLOR_YELLOW}Processes terminated. Exiting.{RESET}")
        sys.exit(0)
