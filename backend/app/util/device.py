import subprocess


def get_video_device_info(device_path: str) -> str:
    """
    Get detailed information of the video device using `v4l2-ctl` command.

    Args:
        device_path (str): Path to the video device.

    Returns:
        str: Detailed information about the video device.
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--device", device_path, "--all"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout
    except Exception as e:
        return f"Error checking device {device_path}: {e}"
