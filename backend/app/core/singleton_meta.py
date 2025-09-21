from abc import ABCMeta
from typing import Any, ClassVar, Dict, Type, TypeVar, cast

T = TypeVar("T")


class SingletonMeta(ABCMeta):
    _instances: ClassVar[Dict[Type[Any], Any]] = {}

    def __call__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls not in SingletonMeta._instances:
            instance = super().__call__(*args, **kwargs)
            SingletonMeta._instances[cls] = instance
        return cast(T, SingletonMeta._instances[cls])
