from typing import List, Optional

from app.schemas.camera import CameraSettings
from app.schemas.stream import StreamSettings
from app.services.detection_service import DetectionSettings
from pydantic import BaseModel


class TextToSpeechItem(BaseModel):
    """
    A model to represent a text to speech item in multiple languages.

    Attributes:
    - `text`: The content of the text.
    - `language`: The language in which the text is written.
    - `default`: Indicator if this text is the default one. Defaults to None.
    """

    text: str
    language: str
    default: Optional[bool] = None


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
    playSound: Optional[List[str]] = None
    resetCameraRotate: Optional[List[str]] = None
    right: Optional[List[str]] = None
    sayText: Optional[List[str]] = None
    stop: Optional[List[str]] = None
    takePhoto: Optional[List[str]] = None
    toggleAvoidObstaclesMode: Optional[List[str]] = None
    toggleCarModelView: Optional[List[str]] = None
    toggleFullscreen: Optional[List[str]] = None
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


class Settings(BaseModel):
    """
    A model to represent the application settings.
    """

    default_music: Optional[str] = None
    default_sound: Optional[str] = None
    default_tts_language: Optional[str] = None
    texts: Optional[List[TextToSpeechItem]] = None
    fullscreen: Optional[bool] = None
    battery_full_voltage: Optional[float] = None
    car_model_view: Optional[bool] = None
    speedometer_view: Optional[bool] = None
    text_info_view: Optional[bool] = None
    auto_download_photo: Optional[bool] = None
    auto_download_video: Optional[bool] = None
    auto_measure_distance_mode: Optional[bool] = None
    auto_measure_distance_delay_ms: Optional[int] = None
    autoplay_music: Optional[bool] = None
    virtual_mode: Optional[bool] = None
    show_player: Optional[bool] = None
    text_to_speech_input: Optional[bool] = None
    show_object_detection_settings: Optional[bool] = True
    keybindings: Optional[Keybindings] = None
    camera: Optional[CameraSettings] = None
    detection: Optional[DetectionSettings] = None
    stream: Optional[StreamSettings] = None


class CalibrationConfig(BaseModel):
    """
    A model to represent the calibration configuration.

    Attributes:
    - `picarx_dir_servo`: Direction servo configuration.
    - `picarx_cam_pan_servo`: Camera pan servo configuration.
    - `picarx_cam_tilt_servo`: Camera tilt servo configuration.
    - `picarx_dir_motor`: Direction motor configuration.
    """

    picarx_dir_servo: Optional[str] = None
    picarx_cam_pan_servo: Optional[str] = None
    picarx_cam_tilt_servo: Optional[str] = None
    picarx_dir_motor: Optional[str] = None
