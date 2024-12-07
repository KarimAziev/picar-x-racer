import time
from typing import List, Optional, TypeVar

from app.adapters.robot_hat.filedb import FileDB
from app.adapters.robot_hat.servo import Servo
from app.config.paths import ROBOT_HAT_CONF

T = TypeVar('T', int, float, str)


class Robot:
    """
    Represents a programmable robot with multiple servos.

    Manages servo control, movements, calibration, and configuration. The class
    is initialized with a list of servo pins and utilizes a configuration file
    to save settings like servo offsets.
    """

    move_list = {}
    """A dictionary of preset actions."""

    max_dps = 428
    """Maximum Degrees Per Second (DPS) a servo is allowed to move."""

    def __init__(
        self,
        pin_list: List[int],
        db=ROBOT_HAT_CONF,
        name: str = "other",
        init_angles: Optional[List[int]] = None,
        init_order=None,
        **kwargs,
    ):
        """
        Initializes the robot.

        Args:
            pin_list: List of integers representing servo pins.
            db: Path to the configuration file for saving settings.
            name: Robot name (used for offsets in the config file).
            init_angles: Initial angles for each servo. Defaults to [0] for all servos.
            init_order: Order in which servos are initialized to avoid power surges.
        """
        super().__init__(**kwargs)
        self.servo_list = []
        self.pin_num = len(pin_list)

        self.name = name

        self.offset_value_name = f"{self.name}_servo_offset_list"

        self.db = FileDB(db=db)
        temp = self.db.get(self.offset_value_name, default_value=str(self.new_list(0)))
        temp = [float(i.strip()) for i in temp.strip("[]").split(",")]

        self.offset = temp

        self.servo_positions = self.new_list(0)

        self.origin_positions = self.new_list(0)
        self.calibrate_position = self.new_list(0)
        self.direction = self.new_list(1)

        if init_angles is None:
            init_angles = [0] * self.pin_num
        elif len(init_angles) != self.pin_num:
            raise ValueError('init angels numbers do not match pin numbers ')

        if init_order == None:
            init_order = range(self.pin_num)

        for i, pin in enumerate(pin_list):
            self.servo_list.append(Servo(pin))
            self.servo_positions[i] = init_angles[i]
        for i in init_order:
            self.servo_list[i].angle(self.offset[i] + self.servo_positions[i])
            time.sleep(0.15)

        self.last_move_time = time.time()

    def new_list(self, default_value: T) -> List[T]:
        """
        Creates a list of length `pin_num` filled with the specified default value.

        Args:
            default_value: The default value to populate the list with.

        Returns:
            A list of length equal to the number of servos, filled with `default_value`.
        """
        return [default_value] * self.pin_num

    def servo_write_raw(self, angle_list):
        """
        Sets servos to the specified raw angles (ignoring offsets).

        Args:
            angle_list: List of raw angles for each servo.
        """
        for i in range(self.pin_num):
            self.servo_list[i].angle(angle_list[i])

    def servo_write_all(self, angles):
        """
        Set servo positions relative to their origin and offsets.

        Combines the given angles with the origin, offset, and servo direction
        to calculate the final servo positions.

        Args:
            angles: A list of servo angles to set.
        """
        relative_angles = []
        for i in range(self.pin_num):
            relative_angles.append(
                self.direction[i]
                * (self.origin_positions[i] + angles[i] + self.offset[i])
            )
        self.servo_write_raw(relative_angles)

    def servo_move(self, targets, speed=50, bpm=None):
        """
        Move servos to target angles at a given speed or beats per minute (BPM).

        Gradually moves each servo to its respective target value, ensuring smooth
        motion and respecting speed limits.

        Args:
            targets: A list of target angles for each servo.
            speed: The speed of motion [0, 100]. Ignored if `bpm` is set.
            bpm: Beats per minute (motion duration is calculated based on this value).
        """
        speed = max(0, speed)
        speed = min(100, speed)
        step_time = 10  # ms
        delta = []
        absdelta = []
        max_step = 0
        steps = []

        for i in range(self.pin_num):
            value = targets[i] - self.servo_positions[i]
            delta.append(value)
            absdelta.append(abs(value))

        max_delta = int(max(absdelta))
        if max_delta == 0:
            time.sleep(step_time / 1000)
            return

        if bpm:
            total_time = 60 / bpm * 1000  # time taken per beat, unit: ms
        else:
            total_time = -9.9 * speed + 1000  # time spent in one step, unit: ms

        current_max_dps = max_delta / total_time * 1000  # dps, degrees per second

        # If current max dps is larger than max dps, then calculate a new total servo move time
        if current_max_dps > self.max_dps:
            total_time = max_delta / self.max_dps * 1000

        max_step = int(total_time / step_time)

        for i in range(self.pin_num):
            step = float(delta[i]) / max_step
            steps.append(step)

        for _ in range(max_step):
            start_timer = time.time()
            delay = step_time / 1000

            for j in range(self.pin_num):
                self.servo_positions[j] += steps[j]
            self.servo_write_all(self.servo_positions)

            servo_move_time = time.time() - start_timer
            delay = delay - servo_move_time
            delay = max(0, delay)
            time.sleep(delay)

    def do_action(self, motion_name, step=1, speed=50):
        """
        Perform a predefined action multiple times.

        Executes a preset motion sequence defined in `move_list` for the robot.

        Args:
            motion_name: The name of the motion to execute.
            step: Number of times to repeat the motion.
            speed: Speed at which the servos should move.
        """
        for _ in range(step):
            for motion in self.move_list[motion_name]:
                self.servo_move(motion, speed)

    def set_offset(self, offset_list):
        """
        Set servo offset values in the database.

        Offsets are clamped between -20 and 20 degrees and applied to all servos.

        Args:
            offset_list: A list of offset values for each servo.
        """
        offset_list = [min(max(offset, -20), 20) for offset in offset_list]
        temp = str(offset_list)
        self.db.set(self.offset_value_name, temp)
        self.offset = offset_list

    def calibration(self):
        """Move all servos to their home (calibration) position."""
        self.servo_positions = self.calibrate_position
        self.servo_write_all(self.servo_positions)

    def reset(self, list=None):
        """
        Reset servo positions to their original or specified state.

        Args:
            position_list: If provided, sets servos to these positions instead
                of their default position.
        """
        if list is None:
            self.servo_positions = self.new_list(0)
            self.servo_write_all(self.servo_positions)
        else:
            self.servo_positions = list
            self.servo_write_all(self.servo_positions)

    def soft_reset(self):
        """
        Gently reset servos to their neutral position.
        """
        temp_list = self.new_list(0)
        self.servo_write_all(temp_list)
