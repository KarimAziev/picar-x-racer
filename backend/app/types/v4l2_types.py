from typing import Literal, TypedDict


class DiscreteFrameSizeConfig(TypedDict):
    type: Literal["discrete"]
    width: int
    height: int


class StepwiseFrameSizeConfig(TypedDict):
    type: Literal["stepwise"]
    min_width: int
    max_width: int
    min_height: int
    max_height: int
    step_width: int
    step_height: int


class ContinuousFrameSizeConfig(TypedDict):
    type: Literal["continuous"]
    min_width: int
    max_width: int
    min_height: int
    max_height: int


class DiscreteFrameIntervalConfig(TypedDict):
    type: Literal["discrete"]
    fps: int


class StepwiseFrameIntervalConfig(TypedDict):
    type: Literal["stepwise"]
    min_fps: int
    max_fps: int
    step_fps: int


class PixelFormatConfig(TypedDict):
    index: int
    pixelformat: int
    description: str


class VideoCaptureFormat(TypedDict):
    width: int
    height: int
    pixel_format: str
