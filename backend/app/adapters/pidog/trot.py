"""
A full MOVE routine divided into 2 sections, where each section is further divided into 3 steps.
This class computes leg coordinate trajectories for a quadruped robot performing a trot gait.
Each leg is represented using a 0-indexed position corresponding to legs 1, 2, 3, and 4.

Leg representation and movement:
  Leg indices: 1, 2, 3, 4 (internally represented as positions 0, 1, 2, 3).
  Leg raise order:
    - Section 1: Legs 1 and 4 are raised.
    - Section 2: Legs 2 and 3 are raised.
  Sections: 2 sections per full move cycle.
  Steps: Each section is divided into 3 steps.

Leg movement details:
  - Legs being raised in a section follow a cosine-based modulation for the y-axis movement (horizontal),
    while a linear interpolation is applied on the z-axis (vertical) to create a lifting effect.
  - Legs not raised are moved forward (or backward) incrementally using a step-down translation,
    keeping the z coordinate fixed at Z_ORIGIN.

Additional parameters:
  - LEG_STEP_WIDTH determines the width of the leg movement.
  - LEG_STEP_HEIGHT defines the maximum elevation during a leg step.
  - CENTER_OF_GRAVITY adjusts the base y-coordinate for stability.
  - LEG_STAND_OFFSET and LEG_STAND_OFFSET_DIRS provide initial offsets for each leg.

The class takes into account modifications for both forward/backward (Direction) and left/right (Sideways)
movements to compute the corresponding leg trajectories throughout the trot cycle.
"""

from math import cos, pi
from typing import List

from app.adapters.pidog.enums import Direction, Sideways


class Trot:
    SECTION_COUNT: int = 2
    STEP_COUNT: int = 3
    LEG_RAISE_ORDER: List[List[int]] = [[1, 4], [2, 3]]
    LEG_STEP_HEIGHT: int = 20
    LEG_STEP_WIDTH: int = 100
    CENTER_OF_GRAVITY: int = -17
    LEG_STAND_OFFSET: int = 5
    Z_ORIGIN: int = 80

    TURNING_RATE: float = 0.5
    LEG_STAND_OFFSET_DIRS: List[int] = [-1, -1, 1, 1]
    LEG_STEP_SCALES_LEFT: List[float] = [TURNING_RATE, 1, TURNING_RATE, 1]
    LEG_STEP_SCALES_MIDDLE: List[float] = [1, 1, 1, 1]
    LEG_STEP_SCALES_RIGHT: List[float] = [1, TURNING_RATE, 1, TURNING_RATE]
    LEG_ORIGINAL_Y_TABLE: List[int] = [0, 1, 1, 0]
    LEG_STEP_SCALES: List[List[float]] = [
        LEG_STEP_SCALES_LEFT,
        LEG_STEP_SCALES_MIDDLE,
        LEG_STEP_SCALES_RIGHT,
    ]

    def __init__(
        self, forward_direction: Direction, sideways_direction: Sideways
    ) -> None:
        """
        Initialize a Trot instance with specified forward/backward and left/right movement.

        Args:
            forward_direction: Direction.FORWARD or Direction.BACKWARD.
            sideways_direction: Sideways.LEFT, Sideways.STRAIGHT, or Sideways.RIGHT.

        Sets the base y-offset based on the chosen movement directions to account for the robot's center of gravity.
        Also computes leg-specific parameters including the stepping widths, section lengths, and leg origin positions.
        """
        self.forward_direction: Direction = forward_direction
        self.sideways_direction: Sideways = sideways_direction

        if self.forward_direction == Direction.FORWARD:
            if self.sideways_direction == Sideways.STRAIGHT:
                self.y_offset: float = 0 + self.CENTER_OF_GRAVITY
            else:
                self.y_offset = -2 + self.CENTER_OF_GRAVITY
        elif self.forward_direction == Direction.BACKWARD:
            if self.sideways_direction == Sideways.STRAIGHT:
                self.y_offset = 8 + self.CENTER_OF_GRAVITY
            else:
                self.y_offset = 1 + self.CENTER_OF_GRAVITY
        else:
            self.y_offset = self.CENTER_OF_GRAVITY

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
        self.leg_offset: List[float] = [
            self.LEG_STAND_OFFSET * self.LEG_STAND_OFFSET_DIRS[i] for i in range(4)
        ]
        self.leg_origin: List[float] = [
            self.leg_step_width[i] / 2
            + self.y_offset
            + (
                self.leg_offset[i]
                * self.LEG_STEP_SCALES[self.sideways_direction + 1][i]
            )
            for i in range(4)
        ]

    def get_coords(self) -> List[List[List[float]]]:
        """
        Calculate and return the coordinates for all legs during the trot cycle.

        The method computes the trajectory for each leg throughout the full move cycle,
        updating the positions based on the raise order defined for each section.
        For raised legs, the y and z positions are calculated using the respective
        _step_y and _step_z functions, while for supporting legs, the y-position is advanced
        by a fixed step-down increment with the z-coordinate maintained at Z_ORIGIN.

        Returns:
            A list containing the coordinate sets for each time step. Each set is a list
            of four [y, z] pairs corresponding to the positions of legs 1, 2, 3, and 4.
        """
        origin_leg_coord: List[List[float]] = [
            [
                self.leg_origin[i]
                - self.LEG_ORIGINAL_Y_TABLE[i] * self.section_length[i],
                self.Z_ORIGIN,
            ]
            for i in range(4)
        ]
        leg_coords: List[List[List[float]]] = []
        for section in range(self.SECTION_COUNT):
            for step in range(self.STEP_COUNT):
                if self.forward_direction == Direction.FORWARD:
                    raise_legs: List[int] = self.LEG_RAISE_ORDER[section]
                else:
                    raise_legs = self.LEG_RAISE_ORDER[self.SECTION_COUNT - section - 1]
                leg_coord: List[List[float]] = []

                for i in range(4):
                    if i + 1 in raise_legs:
                        y: float = self._step_y(i, step)
                        z: float = self._step_z(step)
                    else:
                        y = (
                            origin_leg_coord[i][0]
                            + self.step_down_length[i] * self.forward_direction
                        )
                        z = self.Z_ORIGIN
                    leg_coord.append([y, z])
                origin_leg_coord = leg_coord
                leg_coords.append(leg_coord)
        return leg_coords

    def _step_y(self, leg: int, step: int) -> float:
        """
        Compute the y-coordinate for the raised leg during a step.

        Args:
            leg: The index of the current leg (0-indexed).
            step: The current step within the section.

        Uses a cosine-based modulation to create a smooth horizontal transition for the raised leg.

        Returns:
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
        Compute the z-coordinate for the raised leg during a step.

        Args:
            step: The current step within the section.

        Applies a linear interpolation to the z-axis based on the leg step height.

        Returns:
            The computed z-coordinate as a float.
        """
        return self.Z_ORIGIN - (self.LEG_STEP_HEIGHT * step / (self.STEP_COUNT - 1))
