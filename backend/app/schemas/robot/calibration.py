from app.core.logger import Logger
from app.schemas.robot.motors import MotorDirectionField
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Annotated

logger = Logger(__name__)


class CalibrationConfig(BaseModel):
    """
    A model representing the calibration configuration.
    """

    steering_servo_offset: Annotated[
        float,
        Field(
            ...,
            description="A calibration offset for fine-tuning servo direction angles.",
            examples=[-1.5],
        ),
    ] = 0.0
    cam_pan_servo_offset: Annotated[
        float,
        Field(
            ...,
            description="A calibration offset for fine-tuning camera pan servo angles.",
            examples=[-0.9],
        ),
    ] = 0.0

    cam_tilt_servo_offset: Annotated[
        float,
        Field(
            ...,
            description="A calibration offset for fine-tuning camera tilt servo "
            "angles.",
            examples=[1.3],
        ),
    ] = 0.0

    left_motor_direction: MotorDirectionField = 1
    right_motor_direction: MotorDirectionField = 1

    @field_validator("left_motor_direction", "right_motor_direction")
    def validate_motor_direction(cls, value):
        if value not in (-1, 1):
            raise ValueError("Motor direction must be either 1 or -1.")
        return value


if __name__ == "__main__":
    from pprint import pp

    pp(
        CalibrationConfig(
            steering_servo_offset=2,
            left_motor_direction=-1,
            right_motor_direction=1,
        ).model_dump()
    )
