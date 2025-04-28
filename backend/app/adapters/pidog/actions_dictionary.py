from math import sin
from typing import List, Tuple

from .data_types import ActionAngles, BodyPart
from .enums import Direction, Sideways
from .pidog import Pidog
from .trot import Trot
from .walk import Walk

ActionReturn = Tuple[List[ActionAngles], BodyPart]


class ActionDict(dict):
    def __init__(self, *args: object, **kwargs: object) -> None:
        dict.__init__(self, *args, **kwargs)
        super().__init__()
        self.barycenter: int = -15
        self.height: int = 95

    def __getitem__(self, item: str) -> ActionReturn:
        return getattr(self, item.replace(" ", "_"))

    def set_height(self, height: int) -> None:
        if height in range(20, 95):
            self.height = height

    def set_barycenter(self, offset: int) -> None:
        if offset in range(-60, 60):
            self.barycenter = offset

    @property
    def stand(self) -> ActionReturn:
        x = self.barycenter
        y = 95
        return (
            [
                Pidog.legs_angle_calculation(
                    [[x, y], [x, y], [x + 20, y - 5], [x + 20, y - 5]]
                )
            ],
            "legs",
        )

    @property
    def sit(self) -> ActionReturn:
        return (
            [
                [30, 60, -30, -60, 80, -45, -80, 45],
            ],
            "legs",
        )

    @property
    def lie(self) -> ActionReturn:
        return (
            [
                [45, -45, -45, 45, 45, -45, -45, 45],
            ],
            "legs",
        )

    @property
    def lie_with_hands_out(self) -> ActionReturn:
        return (
            [
                [-60, 60, 60, -60, 45, -45, -45, 45],
            ],
            "legs",
        )

    @property
    def forward(self) -> ActionReturn:
        data: List[ActionAngles] = []
        forward = Walk(
            forward_direction=Direction.FORWARD, sideways_direction=Sideways.STRAIGHT
        )
        coords = forward.get_coords()
        for coord in coords:
            data.append(Pidog.legs_angle_calculation(coord))
        return data, "legs"

    @property
    def backward(self) -> ActionReturn:
        data: List[ActionAngles] = []
        backward = Walk(
            forward_direction=Direction.BACKWARD, sideways_direction=Sideways.STRAIGHT
        )
        coords = backward.get_coords()
        for coord in coords:
            data.append(Pidog.legs_angle_calculation(coord))
        return data, "legs"

    @property
    def turn_left(self) -> ActionReturn:
        data: List[ActionAngles] = []
        turn_left = Walk(
            forward_direction=Direction.FORWARD, sideways_direction=Sideways.LEFT
        )
        coords = turn_left.get_coords()
        for coord in coords:
            data.append(Pidog.legs_angle_calculation(coord))
        return data, "legs"

    @property
    def turn_left_backward(self) -> ActionReturn:
        data: List[ActionAngles] = []
        turn_left = Walk(
            forward_direction=Direction.BACKWARD, sideways_direction=Sideways.LEFT
        )
        coords = turn_left.get_coords()
        for coord in coords:
            data.append(Pidog.legs_angle_calculation(coord))
        return data, "legs"

    @property
    def turn_right(self) -> ActionReturn:
        data: List[ActionAngles] = []
        turn_right = Walk(
            forward_direction=Direction.FORWARD, sideways_direction=Sideways.RIGHT
        )
        coords = turn_right.get_coords()
        for coord in coords:
            data.append(Pidog.legs_angle_calculation(coord))
        return data, "legs"

    @property
    def turn_right_backward(self) -> ActionReturn:
        data: List[ActionAngles] = []
        turn_right = Walk(
            forward_direction=Direction.BACKWARD, sideways_direction=Sideways.RIGHT
        )
        coords = turn_right.get_coords()
        for coord in coords:
            data.append(Pidog.legs_angle_calculation(coord))
        return data, "legs"

    @property
    def trot(self) -> ActionReturn:
        data: List[ActionAngles] = []
        trot = Trot(
            forward_direction=Direction.FORWARD, sideways_direction=Sideways.STRAIGHT
        )
        coords = trot.get_coords()
        for coord in coords:
            data.append(Pidog.legs_angle_calculation(coord))
        return data, "legs"

    @property
    def stretch(self) -> ActionReturn:
        return (
            [
                [-80, 70, 80, -70, -20, 64, 20, -64],
            ],
            "legs",
        )

    @property
    def push_up(self) -> ActionReturn:
        return (
            [
                [90, -30, -90, 30, 80, 70, -80, -70],
                [45, 35, -45, -35, 80, 70, -80, -70],
            ],
            "legs",
        )

    @property
    def doze_off(self) -> ActionReturn:
        start = -30
        am = 20
        anl_f = 0
        anl_b = 0
        angs: List[ActionAngles] = []
        t = 4
        for i in range(0, am + 1):
            anl_f = start + i
            anl_b = 45 - i
            angs += [
                [
                    45.0,
                    float(anl_f),
                    -45.0,
                    -float(anl_f),
                    45.0,
                    -float(anl_b),
                    -45.0,
                    float(anl_b),
                ]
            ] * t
        for _ in range(4):
            anl_f = start + am
            anl_b = 45 - am
            angs += [
                [
                    45.0,
                    float(anl_f),
                    -45.0,
                    -float(anl_f),
                    45.0,
                    -float(anl_b),
                    -45.0,
                    float(anl_b),
                ]
            ] * t
        for i in range(am, -1, -1):
            anl_f = start + i
            anl_b = 45 - i
            angs += [
                [
                    45.0,
                    float(anl_f),
                    -45.0,
                    -float(anl_f),
                    45.0,
                    -float(anl_b),
                    -45.0,
                    float(anl_b),
                ]
            ] * t
        for _ in range(4):
            anl_f = start
            anl_b = 45
            angs += [
                [
                    45.0,
                    float(anl_f),
                    -45.0,
                    -float(anl_f),
                    45.0,
                    -float(anl_b),
                    -45.0,
                    float(anl_b),
                ]
            ] * t

        return angs, "legs"

    @property
    def nod_lethargy(self) -> ActionReturn:
        y = 0
        r = 0
        p = 30
        angs: List[ActionAngles] = []
        for i in range(21):
            r = round(10 * sin(i * 0.314), 2)
            p = round(10 * sin(i * 0.628) - 30, 2)
            if r == -10 or r == 10:
                for _ in range(10):
                    angs.append([y, r, p])
            angs.append([y, r, p])
        return angs, "head"

    @property
    def shake_head(self) -> ActionReturn:
        amplitude = 60
        angs: List[ActionAngles] = []
        for i in range(21):
            _ = round(sin(i * 0.314), 2)
            y1 = amplitude * sin(i * 0.314)
            angs.append([y1, 0, 0])
        return angs, "head"

    @property
    def tilting_head_left(self) -> ActionReturn:
        yaw = 0
        roll = -25
        pitch = 15
        return ([[yaw, roll, pitch]], "head")

    @property
    def tilting_head_right(self) -> ActionReturn:
        yaw = 0
        roll = 25
        pitch = 20
        return ([[yaw, roll, pitch]], "head")

    @property
    def tilting_head(self) -> ActionReturn:
        yaw = 0.0
        roll = 22.0
        pitch = 20.0
        return (([[yaw, roll, pitch]] * 20) + ([[yaw, -roll, pitch]] * 20), "head")

    @property
    def head_bark(self) -> ActionReturn:
        return (
            [
                [0, 0, -40],
                [0, 0, -10],
                [0, 0, -10],
                [0, 0, -40],
            ],
            "head",
        )

    @property
    def wag_tail(self) -> ActionReturn:
        angs: List[ActionAngles] = [[-30], [30]]
        return angs, "tail"

    @property
    def head_up_down(self) -> ActionReturn:
        return (
            [
                [0, 0, 20],
                [0, 0, 20],
                [0, 0, -10],
            ],
            "head",
        )

    @property
    def half_sit(self) -> ActionReturn:
        return (
            [
                [25, 25, -25, -25, 64, -45, -64, 45],
            ],
            "legs",
        )
