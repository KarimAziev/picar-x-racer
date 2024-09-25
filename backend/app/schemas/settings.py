from typing import List, Optional, Union

from pydantic import BaseModel


class Text(BaseModel):
    text: str
    language: str
    default: Optional[bool] = None


class Keybindings(BaseModel):
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
    nextDetectMode: Optional[List[str]] = None
    prevDetectMode: Optional[List[str]] = None
    increaseVolume: Optional[List[str]] = None
    decreaseVolume: Optional[List[str]] = None
    playNextMusicTrack: Optional[List[str]] = None
    playPrevMusicTrack: Optional[List[str]] = None
    nextText: Optional[List[str]] = None
    prevText: Optional[List[str]] = None


class Settings(BaseModel):
    default_music: Optional[str] = None
    default_sound: Optional[str] = None
    texts: Optional[List[Text]] = None
    fullscreen: Optional[bool] = None
    video_feed_quality: Optional[int] = None
    video_feed_detect_mode: Optional[str] = None
    video_feed_enhance_mode: Optional[str] = None
    video_feed_format: Optional[str] = None
    video_feed_fps: Optional[int] = None
    battery_full_voltage: Optional[float] = None
    car_model_view: Optional[bool] = None
    speedometer_view: Optional[bool] = None
    text_info_view: Optional[bool] = None
    auto_download_photo: Optional[bool] = None
    auto_measure_distance_mode: Optional[bool] = None
    auto_measure_distance_delay_ms: Optional[int] = None
    autoplay_music: Optional[bool] = None
    virtual_mode: Optional[bool] = None
    show_player: Optional[bool] = None
    text_to_speech_input: Optional[bool] = None
    keybindings: Optional[Keybindings] = None


class DetectorsResponse(BaseModel):
    detectors: List[str]


class EnhancersResponse(BaseModel):
    enhancers: List[str]


class VideoModesResponse(DetectorsResponse, EnhancersResponse):
    pass


class CalibrationConfig(BaseModel):
    picarx_dir_servo: Optional[str] = None
    picarx_cam_pan_servo: Optional[str] = None
    picarx_cam_tilt_servo: Optional[str] = None
    picarx_dir_motor: Optional[str] = None


class VideoFeedSettings(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    video_feed_fps: int
    video_feed_detect_mode: str | None
    video_feed_enhance_mode: str | None
    video_feed_quality: int
    video_feed_format: str


class VideoFeedUpdateSettings(BaseModel):
    video_feed_detect_mode: Union[str, None] = None
    video_feed_enhance_mode: Union[str, None] = None
    video_feed_format: Union[str, None] = None
    video_feed_quality: Union[int, None] = None
    video_feed_width: Union[int, None] = None
    video_feed_height: Union[int, None] = None
    video_feed_fps: Union[int, None] = None
