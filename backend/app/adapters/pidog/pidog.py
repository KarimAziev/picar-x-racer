import logging
import os
import threading
from math import acos, atan, atan2, cos, pi, sin, sqrt
from pathlib import Path
from time import sleep, time
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from app.config.paths import DEFAULT_SOUNDS_DIR, PX_CALIBRATION_FILE
from app.util.singleton_meta import SingletonMeta
from numpy.typing import ArrayLike
from robot_hat import Battery, Music, Robot
from robot_hat.imu.sh3001 import Sh3001

from .data_types import ActionAngles, BodyPart
from .dual_touch import DualTouch
from .rgb_strip import RGBStrip
from .sound_direction import SoundDirection

""" servos order
                     4,
                   5, '6'
                     |
              3,2 --[ ]-- 7,8
                    [ ]
              1,0 --[ ]-- 10,11
                     |
                    '9'
                    /

    legs pins: [2, 3, 7, 8, 0, 1, 10, 11]
        left front leg, left front leg
        right front leg, right front leg
        left hind leg, left hind leg,
        right hind leg, right hind leg,

    head pins: [4, 6, 5]
        yaw, roll, pitch

    tail pin: [9]
"""

logger = logging.getLogger(__name__)


def compare_version(original_version: str, object_version: str) -> bool:
    or_v = tuple(int(val) for val in original_version.split("."))
    ob_v = tuple(int(val) for val in object_version.split("."))
    return or_v >= ob_v


if compare_version(np.__version__, "2.0.0"):

    def numpy_mat(data: ArrayLike) -> np.matrix:
        return np.asmatrix(data)

else:

    def numpy_mat(data: ArrayLike) -> np.matrix:
        if isinstance(data, np.ndarray):
            return np.matrix(data)
        return np.matrix(data)


class Pidog(metaclass=SingletonMeta):

    # structure constants
    LEG: int = 42
    FOOT: int = 76
    BODY_LENGTH: int = 117
    BODY_WIDTH: int = 98
    BODY_STRUCT: np.matrix = numpy_mat(
        [
            [-BODY_WIDTH / 2, -BODY_LENGTH / 2, 0],
            [BODY_WIDTH / 2, -BODY_LENGTH / 2, 0],
            [-BODY_WIDTH / 2, BODY_LENGTH / 2, 0],
            [BODY_WIDTH / 2, BODY_LENGTH / 2, 0],
        ]
    ).T
    SOUND_DIR: str = DEFAULT_SOUNDS_DIR
    # Servo Speed
    HEAD_DPS: int = 300  # degrees per second
    LEGS_DPS: int = 428
    TAIL_DPS: int = 500
    # PID Constants
    KP: float = 0.033
    KI: float = 0.0
    KD: float = 0.0
    # Default servo pins
    DEFAULT_LEGS_PINS: List[int] = [2, 3, 7, 8, 0, 1, 10, 11]
    DEFAULT_HEAD_PINS: List[int] = [4, 6, 5]
    DEFAULT_TAIL_PIN: List[int] = [9]

    HEAD_PITCH_OFFSET: int = 45

    HEAD_YAW_MIN: int = -90
    HEAD_YAW_MAX: int = 90
    HEAD_ROLL_MIN: int = -70
    HEAD_ROLL_MAX: int = 70
    HEAD_PITCH_MIN: int = -45
    HEAD_PITCH_MAX: int = 30

    def __init__(
        self,
        leg_pins: List[int] = DEFAULT_LEGS_PINS,
        head_pins: List[int] = DEFAULT_HEAD_PINS,
        tail_pin: List[int] = DEFAULT_TAIL_PIN,
        leg_init_angles: Optional[ActionAngles] = None,
        head_init_angles: Optional[ActionAngles] = None,
        tail_init_angle: Optional[ActionAngles] = None,
    ) -> None:
        from .actions_dictionary import ActionDict  # note: dynamically imported

        self.actions_dict = ActionDict()
        self.battery_service = Battery("A4")

        self.body_height: int = 80
        self.pose: np.matrix = numpy_mat(
            [0.0, 0.0, self.body_height]
        ).T  # target position vector
        self.rpy: np.ndarray = (
            np.array([0.0, 0.0, 0.0]) * pi / 180
        )  # Euler angles in radians
        self.leg_point_struc: np.matrix = numpy_mat(
            [
                [-self.BODY_WIDTH / 2, -self.BODY_LENGTH / 2, 0],
                [self.BODY_WIDTH / 2, -self.BODY_LENGTH / 2, 0],
                [-self.BODY_WIDTH / 2, self.BODY_LENGTH / 2, 0],
                [self.BODY_WIDTH / 2, self.BODY_LENGTH / 2, 0],
            ]
        ).T
        self.pitch: float = 0
        self.roll: float = 0

        self.roll_last_error: float = 0
        self.roll_error_integral: float = 0
        self.pitch_last_error: float = 0
        self.pitch_error_integral: float = 0
        self.target_rpy: List[float] = [0, 0, 0]

        if leg_init_angles is None:
            leg_init_angles = self.actions_dict["lie"][0][0]
        if head_init_angles is None:
            head_init_angles = [0.0, 0.0, self.HEAD_PITCH_OFFSET]
        else:
            head_init_angles[2] += self.HEAD_PITCH_OFFSET
        if tail_init_angle is None:
            tail_init_angle = [0.0]

        self.thread_list: List[Union[BodyPart, Literal["imu", "rgb"]]] = []

        try:
            logger.info(f"PX_CALIBRATION_FILE: {PX_CALIBRATION_FILE}")
            self.legs: Robot = Robot(
                pin_list=leg_pins,
                name="legs",
                init_angles=leg_init_angles,
                init_order=[0, 2, 4, 6, 1, 3, 5, 7],
                db=PX_CALIBRATION_FILE,
            )
            self.head: Robot = Robot(
                pin_list=head_pins,
                name="head",
                init_angles=head_init_angles,
                db=PX_CALIBRATION_FILE,
            )
            self.tail: Robot = Robot(
                pin_list=tail_pin,
                name="tail",
                init_angles=tail_init_angle,
                db=PX_CALIBRATION_FILE,
            )
            self.thread_list.extend(["legs", "head", "tail"])
            self.legs.max_dps = self.LEGS_DPS
            self.head.max_dps = self.HEAD_DPS
            self.tail.max_dps = self.TAIL_DPS

            self.legs_action_buffer: List[ActionAngles] = []
            self.head_action_buffer: List[ActionAngles] = []
            self.tail_action_buffer: List[ActionAngles] = []

            self.legs_thread_lock: threading.Lock = threading.Lock()
            self.head_thread_lock: threading.Lock = threading.Lock()
            self.tail_thread_lock: threading.Lock = threading.Lock()

            self.leg_current_angles: Optional[ActionAngles] = leg_init_angles
            self.head_current_angles: ActionAngles = head_init_angles
            self.tail_current_angles: ActionAngles = tail_init_angle

            self.legs_speed: int = 90
            self.head_speed: int = 90
            self.tail_speed: int = 90

            logger.info("done")
        except OSError as err:
            logger.error("fail")
            raise OSError("rotbot_hat I2C init failed. Please try again.") from err

        try:
            logger.info("imu_sh3001 init ... ")
            self.imu: Sh3001 = Sh3001()
            self.imu_acc_offset: List[float] = [0.0, 0.0, 0.0]
            self.imu_gyro_offset: List[float] = [0.0, 0.0, 0.0]
            self.acc_data: List[Union[float, int]] = [0.0, 0.0, 0.0]
            self.gyro_data: List[Union[float, int]] = [0.0, 0.0, 0.0]
            self.imu_fail_count: int = 0
            self.thread_list.append("imu")
            logger.info("imu done")
        except OSError as e:
            logger.error("imu fail %s", e)

        try:
            logger.info("rgb_strip init ... ")
            self.rgb_thread_run: bool = True
            self.rgb_strip: RGBStrip = RGBStrip(addr=0x74, nums=11)
            self.rgb_strip.set_mode("breath", "black")
            self.rgb_fail_count: int = 0
            self.thread_list.append("rgb")
            logger.info("rgb_strip done")
        except OSError as e:
            logger.error("rgb_strip fail %s", e)

        try:
            logger.info("dual_touch init ... ")
            self.dual_touch: DualTouch = DualTouch("D2", "D3")
            self.touch: str = "N"
            logger.info("dual_touch done")
        except Exception as e:
            logger.error("dual_touch fail %s", e)

        try:
            logger.info("sound_direction init ... ")
            self.ears: SoundDirection = SoundDirection()
            logger.info("sound_direction done")
        except Exception as e:
            logger.error("sound_direction fail %s", e)

        try:
            logger.info("sound_effect init ... ")
            self.music: Music = Music()
            logger.info("done")
        except Exception as e:
            logger.error("sound_effect fail %s", e)

        self.distance: Union[float, int] = -1

        self.exit_flag: bool = False
        self.action_threads_start()

    def read_distance(self) -> float:
        return round(self.distance, 2)

    def close_all_thread(self) -> None:
        self.exit_flag = True

    def close(self) -> None:
        import signal
        import sys

        def handler(sig: Any, frame: Any) -> None:
            logger.info("Please wait %s %s", sig, frame)

        signal.signal(signal.SIGINT, handler)

        def _handle_timeout(signum: Any, frame: Any) -> None:
            logger.info("Please wait %s %s", signum, frame)
            raise TimeoutError("function timeout")

        timeout_sec: int = 5
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(timeout_sec)

        logger.info("\rStopping and returning to the initial position ... ")

        try:
            if self.exit_flag is True:
                self.exit_flag = False
                self.action_threads_start()

            self.stop_and_lie()
            self.close_all_thread()

            self.legs_thread.join()
            self.head_thread.join()
            self.tail_thread.join()

            if "rgb" in self.thread_list:
                self.rgb_thread_run = False
                self.rgb_strip_thread.join()
                self.rgb_strip.close()
            if "imu" in self.thread_list:
                self.imu_thread.join()

            logger.info("Quit")
        except Exception as e:
            logger.error(f"Close error: {e}")
        finally:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.alarm(0)
            sys.exit(0)

    def legs_simple_move(self, angles_list: ActionAngles, speed: int = 90) -> None:
        tt: float = time()

        max_delay: float = 0.05
        min_delay: float = 0.005

        if speed > 100:
            speed = 100
        elif speed < 0:
            speed = 0

        delay: float = (100 - speed) / 100 * (max_delay - min_delay) + min_delay

        rel_angles_list: List[float] = []
        for i in range(len(angles_list)):
            rel_angles_list.append(angles_list[i] + self.legs.offset[i])
        self.legs.servo_write_raw(rel_angles_list)

        tt2: float = time() - tt
        delay2: float = 0.001 * len(angles_list) - tt2

        if delay2 < -delay:
            delay2 = -delay
        sleep(delay + delay2)

    def legs_switch(self, flag: bool = False) -> None:
        self.legs_sw_flag = flag

    def action_threads_start(self) -> None:
        if "legs" in self.thread_list:
            self.legs_thread: threading.Thread = threading.Thread(
                name="legs_thread", target=self._legs_action_thread
            )
            self.legs_thread.daemon = True
            self.legs_thread.start()
        if "head" in self.thread_list:
            self.head_thread: threading.Thread = threading.Thread(
                name="head_thread", target=self._head_action_thread
            )
            self.head_thread.daemon = True
            self.head_thread.start()
        if "tail" in self.thread_list:
            self.tail_thread: threading.Thread = threading.Thread(
                name="tail_thread", target=self._tail_action_thread
            )
            self.tail_thread.daemon = True
            self.tail_thread.start()
        if "rgb" in self.thread_list:
            self.rgb_strip_thread: threading.Thread = threading.Thread(
                name="rgb_strip_thread", target=self._rgb_strip_thread
            )
            self.rgb_strip_thread.daemon = True
            self.rgb_strip_thread.start()
        if "imu" in self.thread_list:
            self.imu_thread: threading.Thread = threading.Thread(
                name="imu_thread", target=self._imu_thread
            )
            self.imu_thread.daemon = True
            self.imu_thread.start()

    def _legs_action_thread(self) -> None:
        while not self.exit_flag:
            try:
                with self.legs_thread_lock:
                    self.leg_current_angles = list(self.legs_action_buffer[0])
                self.legs.servo_move(self.leg_current_angles, self.legs_speed)
                with self.legs_thread_lock:
                    self.legs_action_buffer.pop(0)
            except IndexError:
                sleep(0.001)
            except Exception as e:
                logger.error(f"_legs_action_thread Exception: {e}")
                break

    def _head_action_thread(self) -> None:
        while not self.exit_flag:
            try:
                with self.head_thread_lock:
                    self.head_current_angles = list(self.head_action_buffer[0])
                    self.head_action_buffer.pop(0)
                _angles: List[float] = list(self.head_current_angles)
                _angles[0] = self.limit(
                    self.HEAD_YAW_MIN, self.HEAD_YAW_MAX, _angles[0]
                )
                _angles[1] = self.limit(
                    self.HEAD_ROLL_MIN, self.HEAD_ROLL_MAX, _angles[1]
                )
                _angles[2] = self.limit(
                    self.HEAD_PITCH_MIN, self.HEAD_PITCH_MAX, _angles[2]
                )
                _angles[2] += self.HEAD_PITCH_OFFSET
                self.head.servo_move(_angles, self.head_speed)
            except IndexError:
                sleep(0.001)
            except Exception as e:
                logger.error(f"_head_action_thread Exception: {e}")
                break

    def _tail_action_thread(self) -> None:
        while not self.exit_flag:
            try:
                with self.tail_thread_lock:
                    self.tail_current_angles = list(self.tail_action_buffer[0])
                    self.tail_action_buffer.pop(0)
                self.tail.servo_move(self.tail_current_angles, self.tail_speed)
            except IndexError:
                sleep(0.001)
            except Exception as e:
                logger.error(f"_tail_action_thread Exception: {e}")
                break

    def _rgb_strip_thread(self) -> None:
        while self.rgb_thread_run:
            try:
                self.rgb_strip.show()
                self.rgb_fail_count = 0
            except Exception as e:
                self.rgb_fail_count += 1
                sleep(0.001)
                if self.rgb_fail_count > 10:
                    logger.error(f"_rgb_strip_thread Exception: {e}")
                    break

    def _imu_thread(self) -> None:
        _ax: float = 0
        _ay: float = 0
        _az: float = 0
        _gx: float = 0
        _gy: float = 0
        _gz: float = 0
        calibrate_steps: int = 10
        for _ in range(calibrate_steps):
            data = self.imu.read_sensor_data()
            if data is False:
                break
            if data:
                self.acc_data, self.gyro_data = data
            _ax += self.acc_data[0]
            _ay += self.acc_data[1]
            _az += self.acc_data[2]
            _gx += self.gyro_data[0]
            _gy += self.gyro_data[1]
            _gz += self.gyro_data[2]
            sleep(0.1)

        self.imu_acc_offset[0] = round(-16384 - _ax / calibrate_steps, 0)
        self.imu_acc_offset[1] = round(0 - _ay / calibrate_steps, 0)
        self.imu_acc_offset[2] = round(0 - _az / calibrate_steps, 0)
        self.imu_gyro_offset[0] = round(0 - _gx / calibrate_steps, 0)
        self.imu_gyro_offset[1] = round(0 - _gy / calibrate_steps, 0)
        self.imu_gyro_offset[2] = round(0 - _gz / calibrate_steps, 0)

        while not self.exit_flag:
            try:
                data = self.imu.read_sensor_data()
                if data:
                    self.acc_data, self.gyro_data = data
                else:
                    if data is False:
                        self.imu_fail_count += 1
                        if self.imu_fail_count > 10:
                            logger.error("_imu_thread imu data error")
                            break
                    logger.error("IMU data invalid")
                    continue

                self.acc_data[0] += self.imu_acc_offset[0]
                self.acc_data[1] += self.imu_acc_offset[1]
                self.acc_data[2] += self.imu_acc_offset[2]
                self.gyro_data[0] += self.imu_gyro_offset[0]
                self.gyro_data[1] += self.imu_gyro_offset[1]
                self.gyro_data[2] += self.imu_gyro_offset[2]
                ax = self.acc_data[0]
                ay = self.acc_data[1]
                az = self.acc_data[2]
                ay = -ay
                az = -az

                self.pitch = atan(ay / sqrt(ax * ax + az * az)) * 57.2957795
                self.roll = atan(az / sqrt(ax * ax + ay * ay)) * 57.2957795

                self.imu_fail_count = 0
                sleep(0.05)
            except Exception as e:
                self.imu_fail_count += 1
                sleep(0.001)
                if self.imu_fail_count > 10:
                    logger.error(f"_imu_thread Exception: {e}")
                    self.exit_flag = True
                    break

    def legs_stop(self) -> None:
        with self.legs_thread_lock:
            self.legs_action_buffer.clear()
        self.wait_legs_done()

    def head_stop(self) -> None:
        with self.head_thread_lock:
            self.head_action_buffer.clear()
        self.wait_head_done()

    def tail_stop(self) -> None:
        with self.tail_thread_lock:
            self.tail_action_buffer.clear()
        self.wait_tail_done()

    def body_stop(self) -> None:
        self.legs_stop()
        self.head_stop()
        self.tail_stop()

    def legs_move(
        self,
        target_angles: List[ActionAngles],
        immediately: bool = True,
        speed: int = 50,
    ) -> None:
        if immediately:
            self.legs_stop()
        self.legs_speed = speed
        with self.legs_thread_lock:
            self.legs_action_buffer += target_angles

    def head_rpy_to_angle(
        self,
        target_yrp: ActionAngles,
        roll_comp: Union[int, float] = 0,
        pitch_comp: Union[int, float] = 0,
    ) -> List[float]:
        yaw, roll, pitch = target_yrp
        signed: int = -1 if yaw < 0 else 1
        ratio: float = abs(yaw) / 90
        pitch_servo: float = roll * ratio + pitch * (1 - ratio) + pitch_comp
        roll_servo: float = -(signed * (roll * (1 - ratio) + pitch * ratio) + roll_comp)
        yaw_servo = yaw
        return [yaw_servo, roll_servo, pitch_servo]

    def head_move(
        self,
        target_yrps: List[ActionAngles],
        roll_comp: Union[int, float] = 0,
        pitch_comp: Union[int, float] = 0,
        immediately: bool = True,
        speed: int = 50,
    ) -> None:
        if immediately:
            self.head_stop()
        self.head_speed = speed

        angles: List[ActionAngles] = [
            self.head_rpy_to_angle(target_yrp, roll_comp, pitch_comp)
            for target_yrp in target_yrps
        ]
        with self.head_thread_lock:
            self.head_action_buffer += angles

    def head_move_raw(
        self,
        target_angles: List[ActionAngles],
        immediately: bool = True,
        speed: int = 50,
    ) -> None:
        if immediately:
            self.head_stop()
        self.head_speed = speed
        with self.head_thread_lock:
            self.head_action_buffer += target_angles

    def tail_move(
        self,
        target_angles: List[ActionAngles],
        immediately: bool = True,
        speed: int = 50,
    ) -> None:
        if immediately:
            self.tail_stop()
        self.tail_speed = speed
        with self.tail_thread_lock:
            self.tail_action_buffer += target_angles

    def stop_and_lie(self, speed: int = 85) -> None:
        try:
            self.body_stop()
            action_angles = self.actions_dict["lie"][0]
            self.legs_move(action_angles, speed=speed)
            self.head_move_raw([[0, 0, 0]], speed=speed)
            self.tail_move([[0, 0, 0]], speed=speed)
            self.wait_all_done()
            sleep(0.1)
        except Exception as e:
            logger.error(f"stop_and_lie error: {e}")

    def speak(self, name: str, volume: int = 100) -> None:
        sound_file: Optional[str] = None
        for file in os.listdir(self.SOUND_DIR):
            file_path: str = os.path.join(self.SOUND_DIR, file)
            if os.path.isfile(file_path) and Path(file_path).stem == name:
                sound_file = file_path
                break
        self.music.sound_play_threading(sound_file, volume)

    def speak_block(self, name: str, volume: int = 100) -> Optional[bool]:
        if os.path.isfile(name):
            self.music.sound_play(name, volume)
        elif os.path.isfile(self.SOUND_DIR + name + ".mp3"):
            self.music.sound_play(self.SOUND_DIR + name + ".mp3", volume)
        elif os.path.isfile(self.SOUND_DIR + name + ".wav"):
            self.music.sound_play(self.SOUND_DIR + name + ".wav", volume)
        else:
            logger.warning(f"No sound found for {name}")
            return False

    def set_leg_offsets(
        self, cali_list: ActionAngles, reset_list: Optional[ActionAngles] = None
    ) -> None:
        self.legs.set_offset(cali_list)
        if reset_list is None:
            self.legs.reset()
            self.leg_current_angles = [0.0] * 8
        else:
            self.legs.servo_positions = list(reset_list)
            setattr(self.legs, "leg_current_angles", list(reset_list))
            self.legs.servo_write_all(reset_list)

    def set_head_offsets(self, cali_list: ActionAngles) -> None:
        self.head.set_offset(cali_list)
        self.head_move([[0] * 3], immediately=True, speed=80)
        self.head_current_angles = [0] * 3

    def set_tail_offset(self, cali_list: ActionAngles) -> None:
        self.tail.set_offset(cali_list)
        self.tail.reset()
        self.tail_current_angles = [0]

    def set_pose(
        self,
        x: Optional[Union[int, float]] = None,
        y: Optional[Union[int, float]] = None,
        z: Optional[Union[int, float]] = None,
    ) -> None:
        if x is not None:
            self.pose[0, 0] = float(x)
        if y is not None:
            self.pose[1, 0] = float(y)
        if z is not None:
            self.pose[2, 0] = float(z)

    def set_rpy(
        self,
        roll: Optional[Union[int, float]] = None,
        pitch: Optional[Union[int, float]] = None,
        yaw: Optional[Union[int, float]] = None,
        pid: bool = False,
    ) -> None:
        if pid:
            roll_error: float = self.target_rpy[0] - self.roll
            pitch_error: float = self.target_rpy[1] - self.pitch

            roll_offset: float = (
                self.KP * roll_error
                + self.KI * self.roll_error_integral
                + self.KD * (roll_error - self.roll_last_error)
            )
            pitch_offset: float = (
                self.KP * pitch_error
                + self.KI * self.pitch_error_integral
                + self.KD * (pitch_error - self.pitch_last_error)
            )

            self.roll_error_integral += roll_error
            self.pitch_error_integral += pitch_error
            self.roll_last_error = roll_error
            self.pitch_last_error = pitch_error

            roll_offset = roll_offset / 180.0 * pi
            pitch_offset = pitch_offset / 180.0 * pi

            self.rpy[0] += roll_offset
            self.rpy[1] += pitch_offset
        else:
            final_roll: Union[int, float] = (
                self.rpy[0] * 180 / pi if roll is None else roll
            )
            final_pitch: Union[int, float] = (
                self.rpy[1] * 180 / pi if pitch is None else pitch
            )
            final_yaw: Union[int, float] = (
                self.rpy[2] * 180 / pi if yaw is None else yaw
            )
            self.rpy[0] = final_roll / 180.0 * pi
            self.rpy[1] = final_pitch / 180.0 * pi
            self.rpy[2] = final_yaw / 180.0 * pi

    def set_legs(self, legs_list: List[List[float]]) -> None:
        self.legpoint_struc = numpy_mat(
            [
                [
                    -self.BODY_WIDTH / 2,
                    -self.BODY_LENGTH / 2 + legs_list[0][0],
                    self.body_height - legs_list[0][1],
                ],
                [
                    self.BODY_WIDTH / 2,
                    -self.BODY_LENGTH / 2 + legs_list[1][0],
                    self.body_height - legs_list[1][1],
                ],
                [
                    -self.BODY_WIDTH / 2,
                    self.BODY_LENGTH / 2 + legs_list[2][0],
                    self.body_height - legs_list[2][1],
                ],
                [
                    self.BODY_WIDTH / 2,
                    self.BODY_LENGTH / 2 + legs_list[3][0],
                    self.body_height - legs_list[3][1],
                ],
            ]
        ).T

    def pose2coords(self) -> Dict[str, List[List[float]]]:
        roll: float = self.rpy[0]
        pitch: float = self.rpy[1]
        yaw: float = self.rpy[2]

        rotx = numpy_mat(
            [[cos(roll), 0, -sin(roll)], [0, 1, 0], [sin(roll), 0, cos(roll)]]
        )
        roty = numpy_mat(
            [[1, 0, 0], [0, cos(-pitch), -sin(-pitch)], [0, sin(-pitch), cos(-pitch)]]
        )
        rotz = numpy_mat([[cos(yaw), -sin(yaw), 0], [sin(yaw), cos(yaw), 0], [0, 0, 1]])
        rot_mat = rotx * roty * rotz
        AB = numpy_mat(np.zeros((3, 4)))
        for i in range(4):
            AB[:, i] = (
                -self.pose
                - rot_mat * self.BODY_STRUCT[:, i]
                + self.legpoint_struc[:, i]
            )

        body_coor_list: List[List[float]] = []
        for i in range(4):
            body_coor_list.append(
                [
                    float((self.legpoint_struc - AB).T[i, 0]),
                    float((self.legpoint_struc - AB).T[i, 1]),
                    float((self.legpoint_struc - AB).T[i, 2]),
                ]
            )

        leg_coor_list: List[List[float]] = []
        for i in range(4):
            leg_coor_list.append(
                [
                    float(self.legpoint_struc.T[i, 0]),
                    float(self.legpoint_struc.T[i, 1]),
                    float(self.legpoint_struc.T[i, 2]),
                ]
            )

        return {"leg": leg_coor_list, "body": body_coor_list}

    def pose2legs_angle(self) -> List[float]:
        data: Dict[str, List[List[float]]] = self.pose2coords()
        leg_coor_list: List[List[float]] = data["leg"]
        body_coor_list: List[List[float]] = data["body"]
        coords: List[List[float]] = []
        for i in range(4):
            coords.append(
                [
                    leg_coor_list[i][1] - body_coor_list[i][1],
                    body_coor_list[i][2] - leg_coor_list[i][2],
                ]
            )
        angles: List[float] = []
        for i, coord in enumerate(coords):
            leg_angle, foot_angle = self.fieldcoord2polar(coord)
            leg_angle = leg_angle
            foot_angle = foot_angle - 90
            if i % 2 != 0:
                leg_angle = -leg_angle
                foot_angle = -foot_angle
            angles += [leg_angle, foot_angle]
        return angles

    def fieldcoord2polar(self, coord: List[float]) -> Tuple[float, float]:
        y, z = coord
        u: float = sqrt(y**2 + z**2)
        cos_angle1: float = (self.FOOT**2 + self.LEG**2 - u**2) / (
            2 * self.FOOT * self.LEG
        )
        cos_angle1 = min(max(cos_angle1, -1), 1)
        beta: float = acos(cos_angle1)
        angle1: float = atan2(y, z)
        cos_angle2: float = (self.LEG**2 + u**2 - self.FOOT**2) / (2 * self.LEG * u)
        cos_angle2 = min(max(cos_angle2, -1), 1)
        angle2: float = acos(cos_angle2)
        alpha: float = angle2 + angle1 + self.rpy[1]
        alpha = alpha / pi * 180
        beta = beta / pi * 180
        return alpha, beta

    @classmethod
    def coord2polar(cls, coord: List[float]) -> Tuple[float, float]:
        y, z = coord
        u: float = sqrt(y**2 + z**2)
        cos_angle1: float = (cls.FOOT**2 + cls.LEG**2 - u**2) / (2 * cls.FOOT * cls.LEG)
        cos_angle1 = min(max(cos_angle1, -1), 1)
        beta: float = acos(cos_angle1)
        angle1: float = atan2(y, z)
        cos_angle2: float = (cls.LEG**2 + u**2 - cls.FOOT**2) / (2 * cls.LEG * u)
        cos_angle2 = min(max(cos_angle2, -1), 1)
        angle2: float = acos(cos_angle2)
        alpha: float = angle2 + angle1
        alpha = alpha / pi * 180
        beta = beta / pi * 180
        return alpha, beta

    @classmethod
    def legs_angle_calculation(cls, coords: List[List[float]]) -> List[float]:
        translate_list: List[float] = []
        for i, coord in enumerate(coords):
            leg_angle, foot_angle = cls.coord2polar(coord)
            leg_angle = leg_angle
            foot_angle = foot_angle - 90
            if i % 2 != 0:
                leg_angle = -leg_angle
                foot_angle = -foot_angle
            translate_list += [leg_angle, foot_angle]
        return translate_list

    def limit(self, min_val: float, max_val: float, x: float) -> float:
        if x > max_val:
            return max_val
        elif x < min_val:
            return min_val
        else:
            return x

    def do_action(
        self,
        action_name: str,
        step_count: int = 1,
        speed: int = 50,
        pitch_comp: Union[int, float] = 0,
    ) -> None:
        try:
            actions, part = self.actions_dict[action_name]
            if part == "legs":
                for _ in range(step_count):
                    self.legs_move(actions, immediately=False, speed=speed)
            elif part == "head":
                for _ in range(step_count):
                    self.head_move(
                        actions, pitch_comp=pitch_comp, immediately=False, speed=speed
                    )
            elif part == "tail":
                for _ in range(step_count):
                    self.tail_move(actions, immediately=False, speed=speed)
        except KeyError:
            logger.error("do_action: No such action")
        except Exception as e:
            logger.error(f"do_action error: {e}")

    def wait_legs_done(self) -> None:
        while not self.is_legs_done():
            sleep(0.001)

    def wait_head_done(self) -> None:
        while not self.is_head_done():
            sleep(0.001)

    def wait_tail_done(self) -> None:
        while not self.is_tail_done():
            sleep(0.001)

    def wait_all_done(self) -> None:
        self.wait_legs_done()
        self.wait_head_done()
        self.wait_tail_done()

    def is_legs_done(self) -> bool:
        return not bool(len(self.legs_action_buffer) > 0)

    def is_head_done(self) -> bool:
        return not bool(len(self.head_action_buffer) > 0)

    def is_tail_done(self) -> bool:
        return not bool(len(self.tail_action_buffer) > 0)

    def is_all_done(self) -> bool:
        return self.is_legs_done() and self.is_head_done() and self.is_tail_done()

    def get_battery_voltage(self) -> float:
        return self.battery_service.get_battery_voltage()
