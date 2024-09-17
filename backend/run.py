import argparse
import signal
import sys

from app.main import main


def handle_exit(sig, _):
    print(f"Exiting gracefully... {sig}")
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the application.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--debug", action="store_true", help="Set logging level to DEBUG."
    )
    group.add_argument(
        "--log-level",
        default="INFO",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    args = parser.parse_args()

    if args.debug:
        log_level = "DEBUG"
    else:
        log_level = args.log_level

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    main(log_level=log_level)
