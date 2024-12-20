"""
A full MOVE divided into 8 SECTIONs. like below:
leg| 0 | 1 |
====|===|===|
 1  |^^^|___|
 2  |___|^^^|
 3  |___|^^^|
 4  |^^^|___|

4 legs move in this order: 1, 4, 2, 3
there will be a break after every leg move

every SECTION devide into 4 STEPs
"""

from math import cos, pi


class Trot:

    FORWARD = 1
    BACKWARD = -1
    LEFT = -1
    STRAIGHT = 0
    RIGHT = 1

    SECTION_COUNT = 2
    STEP_COUNT = 3
    LEG_RAISE_ORDER = [[1, 4], [2, 3]]
    LEG_STEP_HEIGHT = 20  # the height of the stepping leg
    LEG_STEP_WIDTH = 100  # the width of the stepping leg
    CENTER_OF_GRAVITY = -17  # the body y offset
    LEG_STAND_OFFSET = 5  # the leg center offset
    Z_ORIGIN = 80

    TURNING_RATE = 0.5
    LEG_STAND_OFFSET_DIRS = [-1, -1, 1, 1]
    LEG_STEP_SCALES_LEFT = [TURNING_RATE, 1, TURNING_RATE, 1]
    LEG_STEP_SCALES_MIDDLE = [1, 1, 1, 1]
    LEG_STEP_SCALES_RIGHT = [1, TURNING_RATE, 1, TURNING_RATE]
    LEG_ORIGINAL_Y_TABLE = [0, 1, 1, 0]
    LEG_STEP_SCALES = [
        LEG_STEP_SCALES_LEFT,
        LEG_STEP_SCALES_MIDDLE,
        LEG_STEP_SCALES_RIGHT,
    ]

    def __init__(self, fb, lr):
        """
        Trot init
        fb: FORWARD(1) or BACKWARD(-1)
        lr: LEFT(1), STRAIGHT(0) or RIGHT(-1)
        """
        self.fb = fb
        self.lr = lr

        if self.fb == self.FORWARD:
            if self.lr == self.STRAIGHT:
                self.y_offset = 0 + self.CENTER_OF_GRAVITY
            else:
                self.y_offset = -2 + self.CENTER_OF_GRAVITY
        elif self.fb == self.BACKWARD:
            if self.lr == self.STRAIGHT:
                self.y_offset = 8 + self.CENTER_OF_GRAVITY
            else:
                self.y_offset = 1 + self.CENTER_OF_GRAVITY
        else:
            self.y_offset = self.CENTER_OF_GRAVITY
        self.leg_step_width = [
            self.LEG_STEP_WIDTH * self.LEG_STEP_SCALES[self.lr + 1][i] for i in range(4)
        ]
        self.section_length = [
            self.leg_step_width[i] / (self.SECTION_COUNT - 1) for i in range(4)
        ]
        self.step_down_length = [
            self.section_length[i] / self.STEP_COUNT for i in range(4)
        ]
        self.leg_offset = [
            self.LEG_STAND_OFFSET * self.LEG_STAND_OFFSET_DIRS[i] for i in range(4)
        ]
        self.leg_origin = [
            self.leg_step_width[i] / 2
            + self.y_offset
            + (self.leg_offset[i] * self.LEG_STEP_SCALES[self.lr + 1][i])
            for i in range(4)
        ]

    # Cosine
    def step_y_func(self, leg, step):
        """
        Step function for y axis,
        leg: current leg
        step: current step
        """
        theta = step * pi / (self.STEP_COUNT - 1)
        temp = self.leg_step_width[leg] * (cos(theta) - self.fb) / 2 * self.fb
        y = self.leg_origin[leg] + temp
        return y

    # Linear
    def step_z_func(self, step):
        return self.Z_ORIGIN - (self.LEG_STEP_HEIGHT * step / (self.STEP_COUNT - 1))

    def get_coords(self):
        """
        get coords action coords calculation,
        fb: forward(1) or backward(-1)
        lr: left(1), middle(0) or right(-1)
        """
        origin_leg_coord = [
            [
                self.leg_origin[i]
                - self.LEG_ORIGINAL_Y_TABLE[i] * self.section_length[i],
                self.Z_ORIGIN,
            ]
            for i in range(4)
        ]
        leg_coords = []
        for section in range(self.SECTION_COUNT):
            for step in range(self.STEP_COUNT):
                if self.fb == 1:
                    raise_legs = self.LEG_RAISE_ORDER[section]
                else:
                    raise_legs = self.LEG_RAISE_ORDER[self.SECTION_COUNT - section - 1]
                leg_coord = []

                for i in range(4):
                    if i + 1 in raise_legs:
                        y = self.step_y_func(i, step)
                        z = self.step_z_func(step)
                    else:
                        y = origin_leg_coord[i][0] + self.step_down_length[i] * self.fb
                        z = self.Z_ORIGIN
                    leg_coord.append([y, z])
                origin_leg_coord = leg_coord
                leg_coords.append(leg_coord)
        return leg_coords
