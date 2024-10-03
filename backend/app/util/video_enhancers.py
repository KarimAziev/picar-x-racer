from typing import Tuple

import cv2
import numpy as np
from app.config.font import font
from app.util.logger import Logger
from PIL import Image, ImageDraw

logger = Logger(__name__)


def simulate_robocop_vision(frame: np.ndarray) -> np.ndarray:
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


def simulate_predator_vision(frame: np.ndarray) -> np.ndarray:
    """
    Simulate Predator vision by applying thermal effect.

    Parameters:
        frame (np.ndarray): The input frame to simulate Predator vision.

    Returns:
        np.ndarray: The frame with Predator vision effects.
    """
    thermal_effect = cv2.applyColorMap(frame, cv2.COLORMAP_JET)
    return thermal_effect


def simulate_infrared_vision(frame: np.ndarray) -> np.ndarray:
    """
    Simulate Infrared vision by highlighting warmer areas.

    Parameters:
        frame (np.ndarray): The input frame to simulate Infrared vision.

    Returns:
        np.ndarray: The frame with Infrared vision effects.
    """
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hot_threshold = 150
    _, hot_mask = cv2.threshold(gray_frame, hot_threshold, 255, cv2.THRESH_BINARY)
    hot_mask_colored = cv2.merge([hot_mask, hot_mask, np.zeros_like(hot_mask)])
    infrared_effect = cv2.addWeighted(frame, 0.7, hot_mask_colored, 0.3, 0)
    return infrared_effect


def simulate_ultrasonic_vision(frame: np.ndarray) -> np.ndarray:
    """
    Simulate Ultrasonic vision by creating a monochromatic sonar effect.

    Parameters:
        frame (np.ndarray): The input frame to simulate Ultrasonic vision.

    Returns:
        np.ndarray: The frame with Ultrasonic vision effects.
    """
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_frame, threshold1=50, threshold2=150)
    edges_colored = cv2.merge([edges, edges, edges])
    ultrasonic_effect = cv2.applyColorMap(edges_colored, cv2.COLORMAP_BONE)
    return ultrasonic_effect


def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """
    Preprocess the frame to enhance its quality before detection.

    Args:
        frame (np.ndarray): The input frame.

    Returns:
        np.ndarray: The preprocessed frame.
    """
    # Brightness and contrast
    alpha = 2
    beta = 20
    frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

    # Apply gamma correction
    gamma = 1.5
    inv_gamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv_gamma * 255 for i in np.arange(256)]).astype(
        np.uint8
    )
    frame = cv2.LUT(frame, table)

    # Apply denoising
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    frame = cv2.filter2D(frame, -1, kernel)

    return frame


def preprocess_frame_clahe(frame: np.ndarray) -> np.ndarray:
    """
    Enhance contrast using CLAHE.

    Args:
        frame (np.ndarray): The input frame.

    Returns:
        np.ndarray: The preprocessed frame.
    """
    import cv2

    # Convert to LAB color space
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Apply CLAHE to L-channel
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    # Merge channels and convert back to BGR
    limg = cv2.merge((cl, a, b))
    frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    return frame


def preprocess_frame_edge_enhancement(frame: np.ndarray) -> np.ndarray:
    """
    Enhance edges to highlight object boundaries.

    Args:
        frame (np.ndarray): The input frame.

    Returns:
        np.ndarray: The preprocessed frame.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian Blur to reduce noise
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Apply Canny Edge Detector
    edges = cv2.Canny(gray, threshold1=50, threshold2=150)

    # Define a kernel for dilation
    kernel = np.ones((3, 3), np.uint8)

    # Dilate edges to make them more pronounced
    edges = cv2.dilate(edges, kernel, iterations=1)

    # Convert edges back to BGR format
    edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    # Combine original image with edge information
    frame = cv2.addWeighted(frame, 0.8, edges_color, 0.2, 0)

    return frame


def preprocess_frame_ycrcb(frame: np.ndarray) -> np.ndarray:
    """
    Enhance the image using YCrCb color space transformation.

    Args:
        frame (np.ndarray): The input frame.

    Returns:
        np.ndarray: The preprocessed frame.
    """
    import cv2

    # Convert to YCrCb color space
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)

    # Equalize the Y channel
    ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])

    # Convert back to BGR
    frame = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    return frame


def preprocess_frame_hsv_saturation(frame: np.ndarray) -> np.ndarray:
    """
    Enhance the image by increasing saturation in HSV color space.

    Args:
        frame (np.ndarray): The input frame.

    Returns:
        np.ndarray: The preprocessed frame.
    """
    # Convert to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Equalize the Saturation channel
    hsv[:, :, 1] = cv2.equalizeHist(hsv[:, :, 1])

    # Convert back to BGR
    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    return frame


def preprocess_frame_kmeans(frame: np.ndarray, K: int = 2) -> np.ndarray:
    """
    Apply K-means clustering for image segmentation.

    Args:
        frame (np.ndarray): The input frame.
        K (int): Number of clusters.

    Returns:
        np.ndarray: The preprocessed frame.
    """

    # Reshape image data into a 2D array of pixels and 3 color values (RGB)
    Z: np.ndarray = frame.reshape((-1, 3))
    Z = Z.astype(np.float32)

    # Define criteria
    criteria: Tuple[int, int, float] = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        10,
        1.0,
    )

    # Create initial bestLabels array
    bestLabels: np.ndarray = np.zeros((Z.shape[0], 1), dtype=np.int32)

    # Apply KMeans
    _, labels, centers = cv2.kmeans(
        Z, K, bestLabels, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
    )

    # Convert centers to uint8
    centers: np.ndarray = centers.astype(np.uint8)

    # Flatten labels array
    labels_flattened: np.ndarray = labels.flatten()

    # Map each pixel to its corresponding center
    res: np.ndarray = centers[labels_flattened]

    # Reshape result back to the original image shape
    result_image: np.ndarray = res.reshape((frame.shape))

    return result_image


def preprocess_frame_combined(frame: np.ndarray) -> np.ndarray:
    """
    Apply multiple preprocessing techniques.

    Args:
        frame (np.ndarray): The input frame.

    Returns:
        np.ndarray: The preprocessed frame.
    """
    # Enhance Contrast using CLAHE
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    # Edge Enhancement
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, threshold1=50, threshold2=150)
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    frame = cv2.addWeighted(frame, 0.8, edges_color, 0.2, 0)

    # Sharpening Filter
    kernel_sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    frame = cv2.filter2D(frame, -1, kernel_sharpen)

    return frame
