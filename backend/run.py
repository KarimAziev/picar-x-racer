import argparse

from app.main import main

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
    print(f"starting args {args}")
    log_level = "DEBUG" if args.debug else args.log_level
    main(debug=args.debug, log_level=log_level)
