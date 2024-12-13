from abc import ABCMeta


class SingletonMeta(ABCMeta):
    """
    This is a thread-safe implementation of Singleton.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
