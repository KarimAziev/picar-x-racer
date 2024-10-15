from typing import Dict, List, Optional, Union

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
    nextDetectMode: Optional[List[str]] = None
    prevDetectMode: Optional[List[str]] = None
    increaseVolume: Optional[List[str]] = None
    decreaseVolume: Optional[List[str]] = None
    playNextMusicTrack: Optional[List[str]] = None
    playPrevMusicTrack: Optional[List[str]] = None
    nextText: Optional[List[str]] = None
    prevText: Optional[List[str]] = None
    toggleVideoRecord: Optional[List[str]] = None


class VideoFeedUpdateSettings(BaseModel):
    """
    A model to represent the video feed update settings.

    Attributes:
    - `video_feed_detect_mode`: Detection mode for the video feed.
    - `video_feed_enhance_mode`: Enhancement mode for the video feed.
    - `video_feed_format`: Format of the video feed.
    - `video_feed_quality`: Quality level of the video feed.
    - `video_feed_width`: Width of the video feed.
    - `video_feed_height`: Height of the video feed.
    - `video_feed_fps`: Frames per second for the video feed.
    - `video_feed_confidence`: Confidence level for video feed detection.
    - `video_feed_record`: Flag to record the video.
    - `video_feed_render_fps`: Flag to render actual FPS.
    """

    video_feed_detect_mode: Union[str, None] = None
    video_feed_enhance_mode: Union[str, None] = None
    video_feed_format: Union[str, None] = None
    video_feed_quality: Union[int, None] = None
    video_feed_width: Union[int, None] = None
    video_feed_height: Union[int, None] = None
    video_feed_fps: Union[int, None] = None
    video_feed_confidence: Union[float, None] = None
    video_feed_record: Union[bool, None] = None
    video_feed_device: Union[str, None] = None
    video_feed_pixel_format: Optional[str] = None
    video_feed_render_fps: Optional[bool] = None


class Settings(VideoFeedUpdateSettings):
    """
    A model to represent the application settings.

    Attributes:
    - `default_music`: The default music to play.
    - `default_sound`: The default sound to play.
    - `default_tts_language`: The default language to use in text-to-speech.
    - `texts`: A list of text to speech items.
    - `fullscreen`: Indicator if fullscreen mode is enabled.
    - `video_feed_quality`: Quality level of the video feed.
    - `video_feed_detect_mode`: Detection mode for the video feed.
    - `video_feed_enhance_mode`: Enhancement mode for the video feed.
    - `video_feed_format`: Format of the video feed.
    - `video_feed_fps`: Frames per second for the video feed.
    - `video_feed_confidence`: Confidence level for video feed detection.
    - `battery_full_voltage`: Voltage level considered as full battery.
    - `car_model_view`: Indicator if the car model view is enabled.
    - `speedometer_view`: Indicator if the speedometer view is enabled.
    - `text_info_view`: Indicator if the text information view is enabled.
    - `auto_download_photo`: Indicator if photos are automatically downloaded.
    - `auto_measure_distance_mode`: Indicator if automatic distance measurement mode is enabled.
    - `auto_measure_distance_delay_ms`: Delay in milliseconds for automatic distance measurement.
    - `autoplay_music`: Indicator if music should autoplay.
    - `virtual_mode`: Indicator if virtual mode is enabled. It hides a video stream view and focuses on controlling the car using just a 3D model visualization.
    - `show_player`: Indicator if the player should be shown.
    - `text_to_speech_input`: Indicator if text-to-speech input is enabled.
    - `keybindings`: A list of keybindings.
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
    keybindings: Optional[Keybindings] = None


class DetectorsResponse(BaseModel):
    """
    A model to represent the response for available object detectors.

    Attributes:
    - detectors: A list of video detectors.
    """

    detectors: List[str]


class EnhancersResponse(BaseModel):
    """
    A model to represent the response for video enhancers.

    Attributes:
    - enhancers: A list of video enhancer names.
    """

    enhancers: List[str]


class VideoModesResponse(DetectorsResponse, EnhancersResponse):
    """
    A model to represent the response for both detectors and enhancers.

    Inherits from `DetectorsResponse` and `EnhancersResponse`.
    """

    pass


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


class VideoFeedSettings(BaseModel):
    """
    A model to represent the video feed settings.

    Attributes:
    - `video_feed_confidence`: Confidence level for video feed detection.
    - `video_feed_detect_mode`: Detection mode for the video feed.
    - `video_feed_enhance_mode`: Enhancement mode for the video feed.
    - `video_feed_fps`: Frames per second for the video feed.
    - `video_feed_quality`: Quality level of the video feed.
    - `video_feed_format`: Format of the video feed.
    - `video_feed_width`: Width of the video feed.
    - `video_feed_height`: Height of the video feed.
    - `video_feed_record`: Flag to record the video.
    - `video_feed_device`: Device to use.
    - `video_feed_render_fps`: Flag to render actual FPS.
    """

    video_feed_width: Optional[int] = None
    video_feed_height: Optional[int] = None
    video_feed_fps: int
    video_feed_detect_mode: str | None
    video_feed_enhance_mode: str | None
    video_feed_quality: int
    video_feed_format: str
    video_feed_confidence: float
    video_feed_record: bool
    video_feed_device: Optional[str] = None
    video_feed_pixel_format: Optional[str] = None
    video_feed_render_fps: Optional[bool] = None


class CameraDevicesResponse(BaseModel):
    devices: List[Dict[str, Union[str, List[Dict[str, str]]]]]


class UpdateCameraDevice(BaseModel):
    device: str
