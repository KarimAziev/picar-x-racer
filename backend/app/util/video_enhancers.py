from app.config.font import font
from PIL import Image
import cv2
import numpy as np
from app.util.logger import Logger
from PIL import Image, ImageDraw

logger = Logger(__name__)


def simulate_robocop_vision(
    frame: np.ndarray
) -> np.ndarray:
    """
    Simulate RoboCop vision by applying grayscale conversion,
    edge detection, scan lines, and overlaying a targeting
    reticle and HUD with custom font.

    Parameters:
        frame (np.ndarray): The input frame to simulate RoboCop vision.

    Returns:
        np.ndarray: The frame with RoboCop vision effects.
    """
    # Constants
    target_color = (191, 255, 0)

    # Convert to grayscale
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply edge detection
    edges = cv2.Canny(gray_frame, threshold1=50, threshold2=150)

    # Convert edges to 3 channels and colorize them
    edges_colored = cv2.merge([edges, edges, edges])
    edges_colored[:, :, 0] = 0  # R Channel to 0
    edges_colored[:, :, 2] = 0  # B Channel to 0
    edges_colored[:, :, 1] = edges  # G Channel to the edges intensity

    # Combine the original frame and edges for a composite image
    combined = cv2.addWeighted(frame, 0.7, edges_colored, 0.3, 0)

    # Draw scan lines
    for i in range(0, combined.shape[0], 4):
        cv2.line(combined, (0, i), (combined.shape[1], i), (0, 0, 0), 1)

    # Overlay a targeting reticle
    height, width, _ = combined.shape
    center_x, center_y = width // 2, height // 2

    # Fullsized vertical and horizontal lines
    cv2.line(
        combined,
        (0, center_y),
        (width, center_y),
        target_color,
        2,
    )
    cv2.line(
        combined,
        (center_x, 0),
        (center_x, height),
        target_color,
        2,
    )

    # Convert OpenCV image to PIL Image
    pil_img = Image.fromarray(combined)

    # Prepare font and draw text using PIL
    draw = ImageDraw.Draw(pil_img)

    # Draw the text
    draw.text((10, height - 30), "TARGETING_", font=font, fill=target_color)

    # Convert PIL Image back to OpenCV format
    combined = np.array(pil_img)

    return combined
