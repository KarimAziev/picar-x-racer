import json
import math
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Tuple, Union, cast

from app.schemas.robot.config import HardwareConfig
from app.services.autonomy import (
    ActuationCalibration,
    HardwareController,
    LinearActuatorTranslator,
    MotionArbiter,
    MotionControlService,
    MotionLimits,
    MotionSource,
    RobotMode,
    SelectableDriveHardware,
    TopicBus,
    VirtualDriveHardware,
)
from app.services.autonomy.topics import MOTION_COMMANDED
from app.services.control.car_service import CarService
from app.types.car import PicarState


class FakePicarxAdapter:
    def __init__(self) -> None:
        self.calls: List[Tuple[str, Union[int, float, None]]] = []
        self._state: PicarState = {
            "speed": 0,
            "direction": 0,
            "steering_servo_angle": 0.0,
            "cam_pan_angle": 0.0,
            "cam_tilt_angle": 0.0,
        }

    @property
    def state(self) -> PicarState:
        return self._state

    def forward(self, speed: int) -> None:
        self.calls.append(("forward", speed))
        self._state["speed"] = speed
        self._state["direction"] = 1

    def backward(self, speed: int) -> None:
        self.calls.append(("backward", speed))
        self._state["speed"] = speed
        self._state["direction"] = -1

    def stop(self) -> None:
        self.calls.append(("stop", None))
        self._state["speed"] = 0
        self._state["direction"] = 0

    def set_dir_servo_angle(self, value: float) -> None:
        self.calls.append(("steer", value))
        self._state["steering_servo_angle"] = value


class TestCarServiceMotionControl(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        config_path = Path(__file__).resolve().parents[4] / "config.json"
        config_data = json.loads(config_path.read_text())
        config_data["motion_control"] = {
            "enabled": True,
            "control_frequency_hz": 20,
            "command_timeout_ms": 250,
            "max_forward_speed_mps": 1.0,
            "max_reverse_speed_mps": 0.5,
        }
        self.config = HardwareConfig.model_validate(config_data)
        self.hardware = FakePicarxAdapter()
        self.virtual_hardware = VirtualDriveHardware()
        self.selectable_hardware = SelectableDriveHardware(
            self.hardware,
            self.virtual_hardware,
        )
        steering_radians = math.radians(30)
        limits = MotionLimits(1.0, 0.5, steering_radians)
        controller = HardwareController(
            self.selectable_hardware,
            LinearActuatorTranslator(
                ActuationCalibration(
                    max_forward_speed_mps=1.0,
                    max_reverse_speed_mps=0.5,
                    max_abs_steering_angle_rad=steering_radians,
                    max_forward_command=100,
                    max_reverse_command=100,
                )
            ),
        )
        self.topic_bus = TopicBus()
        self.motion = MotionControlService(
            MotionArbiter(limits),
            controller,
            topic_bus=self.topic_bus,
            drive_hardware=self.selectable_hardware,
        )
        self.car = CarService.__new__(CarService)
        self.car.px = cast(Any, self.hardware)
        self.car.config = self.config
        self.car.motion_control_service = self.motion
        self.car._motion_sequences = {}
        self.car._desired_steering_degrees = 0.0
        self.car.max_speed = 80
        self.car.avoid_obstacles_mode = False
        self.car.distance_service = cast(Any, SimpleNamespace(distance=None))
        self.car.auto_measure_distance_mode = False
        self.car.led_blinking = False

    async def asyncSetUp(self) -> None:
        await self.motion.set_mode(RobotMode.MANUAL)
        self.hardware.calls.clear()

    async def test_manual_percent_command_crosses_si_boundary_without_drift(
        self,
    ) -> None:
        await self.car.handle_move({"direction": 1, "speed": 50})

        self.assertEqual(self.hardware.calls, [("forward", 50)])
        result = self.motion.last_result
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.command.source, MotionSource.MANUAL)
        self.assertEqual(result.command.linear_speed_mps, 0.5)

    async def test_motion_runtime_starts_disarmed(self) -> None:
        await self.car.start_motion_control()
        try:
            self.assertEqual(self.motion.mode, RobotMode.DISARMED)
            self.assertTrue(self.motion.running)
            self.assertIsNotNone(self.motion.last_result)
            assert self.motion.last_result is not None
            self.assertTrue(self.motion.last_result.command.is_stop)
            self.assertEqual(
                self.motion.last_result.command.reason,
                "robot is disarmed",
            )
        finally:
            await self.motion.stop()

    async def test_repeated_command_refreshes_intent_without_rewriting_hardware(
        self,
    ) -> None:
        await self.car.handle_move({"direction": 1, "speed": 50})
        await self.car.handle_move({"direction": 1, "speed": 50})

        self.assertEqual(self.hardware.calls, [("forward", 50)])
        result = self.motion.last_result
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.selected_intent)
        assert result.selected_intent is not None
        self.assertEqual(result.selected_intent.sequence, 2)

    async def test_manual_command_respects_application_speed_limit(self) -> None:
        await self.car.handle_move({"direction": 1, "speed": 100})

        self.assertEqual(self.hardware.calls, [("forward", 80)])
        result = self.motion.last_result
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.command.linear_speed_mps, 0.8)

    async def test_steering_and_stop_also_use_hardware_controller(self) -> None:
        await self.car.handle_move({"direction": 1, "speed": 40})
        self.hardware.calls.clear()

        await self.car.handle_set_servo_dir_angle(15)
        await self.car.handle_stop()

        self.assertEqual(self.hardware.calls[0][0], "steer")
        self.assertAlmostEqual(cast(float, self.hardware.calls[0][1]), 15.0)
        self.assertEqual(self.hardware.calls[-1], ("stop", None))

    async def test_simulated_steering_preserves_virtual_motion_and_ui_state(
        self,
    ) -> None:
        await self.motion.set_simulation_enabled(True)
        await self.motion.set_mode(RobotMode.MANUAL)

        await self.car.handle_move({"direction": 1, "speed": 40})
        await self.car.handle_set_servo_dir_angle(-15)

        self.assertEqual(self.hardware.state["speed"], 0)
        self.assertEqual(self.virtual_hardware.speed, 40)
        self.assertEqual(
            self.virtual_hardware.direction.value,
            "forward",
        )
        self.assertAlmostEqual(self.virtual_hardware.steering_angle_deg, -15)
        self.assertEqual(self.car.current_state["speed"], 40)
        self.assertEqual(self.car.current_state["direction"], 1)
        self.assertAlmostEqual(self.car.current_state["servoAngle"], -15)
        commanded = self.topic_bus.latest(MOTION_COMMANDED)
        self.assertIsNotNone(commanded)
        assert commanded is not None
        self.assertAlmostEqual(commanded.steering_angle_rad, math.radians(-15))

        await self.car.handle_stop()

        self.assertEqual(self.virtual_hardware.speed, 0)
        self.assertEqual(self.car.current_state["speed"], 0)
        self.assertEqual(self.car.current_state["direction"], 0)
        self.assertAlmostEqual(self.car.current_state["servoAngle"], -15)

    async def test_emergency_stop_handler_latches_until_clear(self) -> None:
        await self.car.handle_move({"direction": 1, "speed": 40})

        await self.car.handle_emergency_stop("web operator")

        self.assertEqual(self.motion.mode, RobotMode.ESTOP)
        self.assertEqual(self.motion.estop_reason, "web operator")
        self.assertEqual(self.hardware.calls[-1], ("stop", None))

        await self.car.handle_clear_emergency_stop()

        self.assertEqual(self.motion.mode, RobotMode.DISARMED)

    async def test_safety_modes_cannot_be_selected_through_generic_mode_action(
        self,
    ) -> None:
        for mode in ["estop", "fault"]:
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "dedicated"):
                    await self.car.handle_set_robot_mode(mode)


if __name__ == "__main__":
    unittest.main()
