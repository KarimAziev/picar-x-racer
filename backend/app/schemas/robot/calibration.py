from app.core.logger import Logger
from app.schemas.robot.motors import MotorDirectionField
from pydantic import BaseModel, Field, field_validator
from typing import List
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

    motor_directions: Annotated[
        List[MotorDirectionField], Field(min_length=1, max_length=2)
    ] = Field(default_factory=lambda: [1, 1])

    @field_validator("motor_directions")
    def validate_motor_direction(
        cls, value: List[MotorDirectionField]
    ) -> List[MotorDirectionField]:
        if any(direction not in (-1, 1) for direction in value):
            raise ValueError("Motor direction must be either 1 or -1.")
        return value


if __name__ == "__main__":
    from pprint import pp

    pp(
        CalibrationConfig(
            steering_servo_offset=2,
            motor_directions=[-1, 1],
        ).model_dump()
    )
