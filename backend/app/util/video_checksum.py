import os

from app.core.logger import Logger

logger = Logger(__name__)


def get_dev_video_checksum() -> str:
    """
    Return a checksum-like string based on the number and metadata of `/dev/video*`.
    This helps to cache lists of video devices but detects if any device is added/removed.

    Returns:
    --------
    A unique string that changes when `/dev/video*` devices change.
    """
    try:
        dev_dir = "/dev"
        video_devices = [
            name for name in os.listdir(dev_dir) if name.startswith("video")
        ]
        video_devices.sort()

        timestamps = [
            os.stat(os.path.join(dev_dir, dev)).st_mtime for dev in video_devices
        ]
        return f"{len(video_devices)}:{sum(timestamps)}"
    except Exception as e:
        logger.error("Failed to compute dev/video checksum: %s", e)
        return "error"
