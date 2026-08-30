from typing import TypedDict, Union

from robot_hat.services.motor_service import MotorServiceDirection


class PicarBaseState(TypedDict):
    speed: float
    direction: MotorServiceDirection


class PicarState(PicarBaseState):
    steering_servo_angle: float
    cam_pan_angle: float
    cam_tilt_angle: float


class CarServiceState(PicarBaseState):
    servoAngle: float
    camPan: float
    camTilt: float
    maxSpeed: Union[int, None]
    avoidObstacles: bool
    distance: float
    autoMeasureDistanceMode: Union[bool, None]
    ledBlinking: bool
    motionControlEnabled: bool
    robotMode: str
    motionGeneration: int
    motionReason: Union[str, None]
    motionSource: Union[str, None]
    emergencyStop: bool
    motionFault: Union[str, None]


class CarServiceBroadcastPayload(TypedDict):
    type: str
    payload: PicarBaseState
