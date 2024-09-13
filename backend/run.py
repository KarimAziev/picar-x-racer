import signal
import sys

from app.main import main


def handle_exit(sig, _):
    print(f"Exiting gracefully... {sig}")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    main()
