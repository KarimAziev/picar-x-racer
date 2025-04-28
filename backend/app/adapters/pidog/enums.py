from enum import IntEnum


class Direction(IntEnum):
    FORWARD = 1
    BACKWARD = -1


class Sideways(IntEnum):
    LEFT = -1
    STRAIGHT = 0
    RIGHT = 1
