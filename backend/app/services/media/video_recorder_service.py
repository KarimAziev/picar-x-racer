import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import cv2
import numpy as np
from app.core.logger import Logger

if TYPE_CHECKING:
    from app.services.file_management.file_manager_service import FileManagerService

logger = Logger(__name__)


class VideoRecorderService:
    """
    A class responsible for handling video recording functionality.

    The class allows for starting, writing frames to, and safely stopping
    video recordings.
    """

    def __init__(self, file_manager: "FileManagerService") -> None:
        self.file_manager = file_manager
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.current_video_path: Optional[str] = None
        self.video_file_service = self.file_manager

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
        video_dir_path = Path(self.video_file_service.root_directory)
        video_dir_path.mkdir(exist_ok=True, parents=True)

        fourcc = cv2.VideoWriter.fourcc(*"MP4V")
        file_name = f"recording_{time.strftime('%Y-%m-%d-%H-%M-%S')}.mp4"
        video_path = video_dir_path.joinpath(file_name).as_posix()

        logger.info(f"Recording video at {video_path}, {width}x{height}, {fps}")
        self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        self.current_video_path = video_path

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
            logger.info("Releasing video writer")
            self.video_writer.release()
            logger.info("video writer released")
            self.video_writer = None
