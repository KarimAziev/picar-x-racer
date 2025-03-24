from typing import List, Optional

from app.schemas.battery import BatterySettings
from app.schemas.camera import CameraSettings
from app.schemas.music import MusicSettings
from app.schemas.stream import StreamSettings
from app.schemas.tts import TTSSettings
from app.services.detection.detection_service import DetectionSettings
from app.util.pydantic_helpers import partial_model
from pydantic import BaseModel, Field


class Keybindings(BaseModel):
    """
    A model to represent keybindings for various actions.
    """

    accelerate: Optional[List[str]] = None
    decelerate: Optional[List[str]] = None
    decreaseCamPan: Optional[List[str]] = None
    decreaseCamTilt: Optional[List[str]] = None
    decreaseMaxSpeed: Optional[List[str]] = None
    decreaseQuality: Optional[List[str]] = None
    getBatteryVoltage: Optional[List[str]] = None
    getDistance: Optional[List[str]] = None
    increaseCamPan: Optional[List[str]] = None
    increaseCamTilt: Optional[List[str]] = None
    increaseMaxSpeed: Optional[List[str]] = None
    increaseQuality: Optional[List[str]] = None
    left: Optional[List[str]] = None
    openGeneralSettings: Optional[List[str]] = None
    openShortcutsSettings: Optional[List[str]] = None
    playMusic: Optional[List[str]] = None
    resetCameraRotate: Optional[List[str]] = None
    right: Optional[List[str]] = None
    sayText: Optional[List[str]] = None
    stop: Optional[List[str]] = None
    takePhoto: Optional[List[str]] = None
    toggleAvoidObstaclesMode: Optional[List[str]] = None
    toggleCarModelView: Optional[List[str]] = None
    toggleSpeedometerView: Optional[List[str]] = None
    toggleTextInfo: Optional[List[str]] = None
    toggleVirtualMode: Optional[List[str]] = None
    toggleAutoMeasureDistanceMode: Optional[List[str]] = None
    toggleAutoDownloadPhoto: Optional[List[str]] = None
    toggleCalibration: Optional[List[str]] = None
    increaseFPS: Optional[List[str]] = None
    decreaseFPS: Optional[List[str]] = None
    increaseDimension: Optional[List[str]] = None
    decreaseDimension: Optional[List[str]] = None
    nextEnhanceMode: Optional[List[str]] = None
    prevEnhanceMode: Optional[List[str]] = None
    toggleDetection: Optional[List[str]] = None
    increaseVolume: Optional[List[str]] = None
    decreaseVolume: Optional[List[str]] = None
    playNextMusicTrack: Optional[List[str]] = None
    playPrevMusicTrack: Optional[List[str]] = None
    nextText: Optional[List[str]] = None
    prevText: Optional[List[str]] = None
    toggleVideoRecord: Optional[List[str]] = None
    slowdown: Optional[List[str]] = None
    toggleAudioStreaming: Optional[List[str]] = None


class General(BaseModel):
    """
    A model representing general application settings.
    """

    auto_download_photo: Optional[bool] = Field(
        None,
        description="Enables or disables the automatic downloading of captured photos.",
        examples=[True, False],
    )
    auto_download_video: Optional[bool] = Field(
        None,
        description="Enables or disables the automatic downloading of recorded videos.",
        examples=[True, False],
    )
    robot_3d_view: Optional[bool] = Field(
        None,
        description="Whether to display the robot's 3D model.",
        examples=[True, False],
    )
    virtual_mode: Optional[bool] = Field(
        None,
        description="Replaces the live camera feed with a 3D virtual model when enabled.",
        examples=[True, False],
    )
    show_player: Optional[bool] = Field(
        None,
        description="Whether to display the visibility of the music player interface.",
        examples=[True, False],
    )
    speedometer_view: Optional[bool] = Field(
        None,
        description="Enables or disables the speedometer display.",
        examples=[True, False],
    )
    text_to_speech_input: Optional[bool] = Field(
        None,
        description="Shows or hides the input field for the text-to-speech feature.",
        examples=[True, False],
    )
    text_info_view: Optional[bool] = Field(
        None,
        description="Whether to display the text-based information, such as camera tilt, "
        "camera pan, and servo direction.",
        examples=[True, False],
    )
    show_object_detection_settings: Optional[bool] = Field(
        None,
        description="Whether to display the object detection settings panel on the main screen.",
        examples=[True, False],
    )
    show_audio_stream_button: Optional[bool] = Field(
        None,
        description="Whether to display the audio stream icon button.",
        examples=[True, False],
    )
    show_auto_measure_distance_button: Optional[bool] = Field(
        None,
        description="Whether to display the auto-measure distance button.",
        examples=[True, False],
    )
    show_photo_capture_button: Optional[bool] = Field(
        None,
        description="Whether to display the photo capture icon button.",
        examples=[True, False],
    )
    show_video_record_button: Optional[bool] = Field(
        None,
        description="Whether to display the video record icon button.",
        examples=[True, False],
    )
    show_battery_indicator: Optional[bool] = Field(
        None,
        description="Whether to display the battery indicator.",
        examples=[True, False],
    )
    show_connections_indicator: Optional[bool] = Field(
        None,
        description="Whether to display the active connections counter.",
        examples=[True, False],
    )

    show_shutdown_reboot_button: Optional[bool] = Field(
        None,
        description="Whether to display the shutdown and reboot control buttons.",
        examples=[True, False],
    )

    show_fullscreen_button: Optional[bool] = Field(
        None,
        description="Whether to display the request full screen button.",
        examples=[True, False],
    )
    show_avoid_obstacles_button: Optional[bool] = Field(
        None,
        description="Whether to display the button to toggle the avoid obstacle mode.",
        examples=[True, False],
    )

    show_dark_theme_toggle: Optional[bool] = Field(
        None,
        description="Whether to display the dark theme toggle button in the top right corner of the screen.",
        examples=[False, True],
    )


class RobotSettings(BaseModel):
    """
    A model representing settings related to robot control.
    """

    max_speed: Optional[int] = Field(
        None,
        ge=10,
        le=100,
        description="The maximum speed of the robot, measured in units. Valid values range from 10 to 100.",
        examples=[50, 60, 70, 80, 90, 100],
    )
    auto_measure_distance_mode: Optional[bool] = Field(
        None,
        description="Enables or disables the automatic measurement of distances using ultrasonic sensors.",
        examples=[True, False],
    )
    auto_measure_distance_delay_ms: Optional[int] = Field(
        None,
        ge=500,
        description="The time interval, in milliseconds, between successive automatic distance measurements. "
        "This is applicable only when `auto_measure_distance_mode` is enabled. "
        "The value must be at least 500 ms.",
        examples=[1000, 2000],
    )


class Settings(BaseModel):
    """
    A model representing application-wide settings.
    """

    battery: BatterySettings = Field(
        ..., description="Configuration for battery settings."
    )

    general: General = Field(
        ...,
        description="General application settings, including UI widget visibility.",
    )

    robot: RobotSettings = Field(..., description="Settings related to robot control.")

    camera: CameraSettings = Field(
        ...,
        description="Configuration settings for the camera, including resolution, FPS, and device input.",
    )
    detection: DetectionSettings = Field(
        ...,
        description="Settings for the object detection module, including model choice, thresholds, and parameters.",
    )
    stream: StreamSettings = Field(
        ...,
        description="Settings defining the video stream output, such as format, quality, and enhancement modes.",
    )

    tts: TTSSettings = Field(..., description="Text to speech settings.")

    music: MusicSettings = Field(
        ...,
        description="Settings for the music playback system, including configurations for track control and playback behavior.",
    )
    keybindings: Keybindings = Field(
        ...,
        description="A collection of custom keybindings for various user actions.",
        examples=[
            {
                "accelerate": ["w"],
                "decelerate": ["s"],
                "decreaseCamPan": ["ArrowLeft"],
                "decreaseCamTilt": ["ArrowDown"],
            }
        ],
    )


@partial_model
class SettingsUpdateRequest(Settings):
    pass
