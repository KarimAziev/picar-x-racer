def print_initial_message(browser_url: str):
    """
    Print an initial message to the terminal indicating that the app is ready.

    This function prints a message with styled ANSI color and bold attributes
    indicating to the user that the app is ready. The message provides the
    user with the URL to open the app in a browser. The text appears with bold
    and magenta foreground color.

    Args:
        browser_url (str): The URL to open the app in the web browser.
    """
    BOLD = "\033[1m"
    RESET = "\033[0m"
    MAGENTA_FG = "\033[35m"
    FG_COLOR = MAGENTA_FG

    print(f"")
    print(f"")
    print(f"{BOLD}{FG_COLOR}🚗 App is ready. Open in the browser:{RESET}")
    print("")
    print(f"{BOLD}{FG_COLOR}{browser_url}{RESET}")
    print("")
    print("")
