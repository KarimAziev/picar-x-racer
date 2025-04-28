"""
A full MOVE routine divided into 8 sections. Each section is further divided into 6 steps.
The class computes leg coordinate trajectories for a robotic walker, where four legs move
in a specific order, and each leg following a calculated path in both the y (horizontal) and
z (vertical) axes.

Leg representation and movement:
  Leg indices: 1, 2, 3, 4 are represented using 0-indexed positions internally.
  Leg order: The order in which legs are raised is given by the list:
             [1, 0, 4, 0, 2, 0, 3, 0]
  Sections: 8 sections per full move.
  Steps: Each section is divided into 6 steps.

leg| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7
====|===|===|===|===|===|===|===|===
 1  |^^^|___|___|___|___|___|___|___
 2  |___|___|___|___|^^^|___|___|___
 3  |___|___|___|___|___|___|^^^|___
 4  |___|___|^^^|___|___|___|___|___

The class uses cosine-based modulation for the y-axis movement during the stepping phase,
and a linearly decreasing function for the z-axis (vertical) displacement.
"""

from math import cos, pi
from typing import List

from app.adapters.pidog.enums import Direction, Sideways


class Walk:
    SECTION_COUNT: int = 8
    STEP_COUNT: int = 6
    LEG_ORDER: List[int] = [1, 0, 4, 0, 2, 0, 3, 0]
    LEG_STEP_HEIGHT: int = 20
    LEG_STEP_WIDTH: int = 80
    CENTER_OF_GRAVIRTY: int = -15
    LEG_POSITION_OFFSETS: List[int] = [-10, -10, 20, 20]
    Z_ORIGIN: int = 80

    TURNING_RATE: float = 0.3
    LEG_STEP_SCALES_LEFT: List[float] = [TURNING_RATE, 1, TURNING_RATE, 1]
    LEG_STEP_SCALES_MIDDLE: List[float] = [1, 1, 1, 1]
    LEG_STEP_SCALES_RIGHT: List[float] = [1, TURNING_RATE, 1, TURNING_RATE]
    LEG_ORIGINAL_Y_TABLE: List[int] = [0, 2, 3, 1]
    LEG_STEP_SCALES: List[List[float]] = [
        LEG_STEP_SCALES_LEFT,
        LEG_STEP_SCALES_MIDDLE,
        LEG_STEP_SCALES_RIGHT,
    ]

    def __init__(
        self, forward_direction: Direction, sideways_direction: Sideways
    ) -> None:
        """
        Initialize an instance with specified forward/backward and left/right movement.

        Args:
        --------------
           - forward_direction: Direction.FORWARD or Direction.BACKWARD.
           - sideways_direction: Sideways.LEFT, Sideways.STRAIGHT, or Sideways.RIGHT.
        """
        self.forward_direction = forward_direction
        self.sideways_direction = sideways_direction

        if self.forward_direction == Direction.FORWARD:
            if self.sideways_direction == Sideways.STRAIGHT:
                self.y_offset: float = 0 + self.CENTER_OF_GRAVIRTY
            else:
                self.y_offset = 0 + self.CENTER_OF_GRAVIRTY
        elif self.forward_direction == Direction.BACKWARD:
            if self.sideways_direction == Sideways.STRAIGHT:
                self.y_offset = 0 + self.CENTER_OF_GRAVIRTY
            else:
                self.y_offset = 0 + self.CENTER_OF_GRAVIRTY
        else:
            self.y_offset = self.CENTER_OF_GRAVIRTY

        self.leg_step_width: List[float] = [
            self.LEG_STEP_WIDTH * self.LEG_STEP_SCALES[self.sideways_direction + 1][i]
            for i in range(4)
        ]
        self.section_length: List[float] = [
            self.leg_step_width[i] / (self.SECTION_COUNT - 1) for i in range(4)
        ]
        self.step_down_length: List[float] = [
            self.section_length[i] / self.STEP_COUNT for i in range(4)
        ]
        self.leg_origin: List[float] = [
            self.leg_step_width[i] / 2
            + self.y_offset
            + (
                self.LEG_POSITION_OFFSETS[i]
                * self.LEG_STEP_SCALES[self.sideways_direction + 1][i]
            )
            for i in range(4)
        ]

    def get_coords(self) -> List[List[List[float]]]:
        """
        Calculate and return the coordinates for all legs during the walk cycle.

        Returns:
        --------------
        A list containing the coordinate sets for each time step, where each set is a list
        of four [y, z] pairs representing each leg.
        """
        origin_leg_coord: List[List[float]] = [
            [
                self.leg_origin[i]
                - self.LEG_ORIGINAL_Y_TABLE[i] * 2 * self.section_length[i],
                self.Z_ORIGIN,
            ]
            for i in range(4)
        ]
        leg_coord: List[List[float]] = origin_leg_coord.copy()
        leg_coords: List[List[List[float]]] = []

        for section in range(self.SECTION_COUNT):
            for step in range(self.STEP_COUNT):
                if self.forward_direction == Direction.FORWARD:
                    raise_leg: int = self.LEG_ORDER[section]
                else:
                    raise_leg = self.LEG_ORDER[self.SECTION_COUNT - section - 1]

                for i in range(4):
                    if raise_leg != 0 and i == raise_leg - 1:
                        y: float = self._step_y(i, step)
                        z: float = self._step_z(step)
                    else:
                        y = (
                            leg_coord[i][0]
                            + self.step_down_length[i] * self.forward_direction
                        )
                        z = self.Z_ORIGIN
                    leg_coord[i] = [y, z]

                leg_coords.append(leg_coord.copy())

        leg_coords.append(origin_leg_coord.copy())
        return leg_coords

    def _step_y(self, leg: int, step: int) -> float:
        """
        Compute the y-coordinate for a given leg during a step, using a cosine-based modulation.

        Args:
        --------------
        - leg: Index of the leg (0-indexed).
        - step: The current step count for the section.

        Returns:
        --------------
        The computed y-coordinate as a float.
        """
        theta: float = step * pi / (self.STEP_COUNT - 1)
        temp: float = (
            self.leg_step_width[leg]
            * (cos(theta) - self.forward_direction)
            / 2
            * self.forward_direction
        )
        y: float = self.leg_origin[leg] + temp
        return y

    def _step_z(self, step: int) -> float:
        """
        Compute the z-coordinate for the leg being lifted during a step.

        Args:
        --------------
        - step: The current step count within the section.

        Returns:
        --------------
        The computed z-coordinate as a float.
        """
        return self.Z_ORIGIN - (self.LEG_STEP_HEIGHT * step / (self.STEP_COUNT - 1))
