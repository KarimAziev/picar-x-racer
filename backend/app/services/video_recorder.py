"""
Module: video_recorder
Description: Provides functionalities to record video sequences. This module
contains the `VideoRecorder` class which is implemented as a singleton.
The class allows for starting, writing frames to, and safely stopping
video recordings. Utilizes OpenCV for video operations.
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import cv2
import numpy as np
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta

if TYPE_CHECKING:
    from app.services.file_service import FileService

logger = Logger(__name__)


class VideoRecorder(metaclass=SingletonMeta):
    """
    A singleton class responsible for handling video recording functionality.
    """

    def __init__(self, file_manager: "FileService"):
        self.file_manager = file_manager
        self.video_writer: Optional[cv2.VideoWriter] = None

    def start_recording(self, width: int, height: int, fps: float) -> None:
        """
        Starts a new video recording session.

        This method initializes the video writer and sets up the file path for storing
        the recorded video.

        Args:
            width: The width of the video frame.
            height: The height of the video frame.
            fps: The frame rate (frames per second) of the video.

        Raises:
            Exception: If the video directory cannot be created or video writer fails to initialize.
        """
        video_dir_path = Path(self.file_manager.user_videos_dir)
        video_dir_path.mkdir(exist_ok=True, parents=True)

        fourcc = cv2.VideoWriter.fourcc(*"H264")
        file_name = f"recording_{time.strftime('%Y-%m-%d-%H-%M-%S')}.avi"
        video_path = video_dir_path.joinpath(file_name).as_posix()

        logger.info(f"Recording video at {video_path}, {width}x{height}, {fps}")
        self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    def write_frame(self, frame: np.ndarray) -> None:
        """
        Writes a single frame to the video.

        Args:
            frame (np.ndarray): The video frame to be written to the output video.

        Raises:
            Exception: If the video writer is not properly initialized.
        """
        if self.video_writer:
            self.video_writer.write(frame)

    def stop_recording_safe(self) -> None:
        """
        Safely stops the video recording session.

        This method attempts to release the video writer and logs an error
        if an exception occurs during the process.
        """
        try:
            self.stop_recording()
        except Exception:
            logger.error("Error releasing video writer", exc_info=True)

    def stop_recording(self) -> None:
        """
        Stops the video recording session.

        Releases the OpenCV video writer and sets it to None.
        """
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
