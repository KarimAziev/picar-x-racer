from app.core.logger import Logger as MainLogger


class Logger(MainLogger):
    def __init__(self, name: str, app_name="px_robot"):
        super().__init__(name, app_name)
