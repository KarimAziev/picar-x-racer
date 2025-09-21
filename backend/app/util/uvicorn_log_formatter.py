from logging import INFO, Formatter


class UvicornFormatter(Formatter):
    def __init__(self, fmt=None, datefmt=None, use_colors=None) -> None:
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record) -> str:
        record.name = ""
        if self.use_colors and record.levelno == INFO:
            record.msg = f"\033[92m{record.msg}\033[0m"
        return super().format(record)
