from typing import Tuple

import cv2
import numpy as np
from app.core.logger import Logger

logger = Logger(__name__)


def simulate_robocop_vision(
    frame: np.ndarray, line_thickness: int = 1, line_spacing: int = 2
) -> np.ndarray:
    """
    Simulate RoboCop vision by creating alternating lines of:

    - Original frame line.
    - Lightened frame line with specific thickness (thin lightened lines).

    Parameters:
        frame (np.ndarray): The input frame to simulate RoboCop vision.
        line_thickness (int): The thickness of the lightened lines.
        line_spacing (int): The number of rows in between lightened lines.

    Returns:
        np.ndarray: The frame with alternating lightened scan lines.
    """

    white_image = np.ones_like(frame) * 255
    opacity = 0.8  # lightness of the scan lines (from 0 to 1, as in CSS)
    lightened_frame = cv2.addWeighted(frame, opacity, white_image, 1 - opacity, 0)

    result_frame = np.copy(frame)

    for i in range(0, frame.shape[0], line_spacing + line_thickness):
        # Replace a block of rows with lightened frame rows (thin lightened lines)
        result_frame[i : i + line_thickness] = lightened_frame[i : i + line_thickness]

    return result_frame


def simulate_predator_vision(frame: np.ndarray) -> np.ndarray:
    """
    Simulate Predator vision by applying thermal effect.

    Parameters:
        frame (np.ndarray): The input frame to simulate Predator vision.

    Returns:
        np.ndarray: The frame with Predator vision effects.
    """
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Amplify the saturation to enhance colors
    hsv_frame[:, :, 1] = np.clip(
        hsv_frame[:, :, 1].astype(np.float32) * 2, 0, 255
    ).astype(np.uint8)

    # Convert back to BGR color space
    saturated_frame = cv2.cvtColor(hsv_frame, cv2.COLOR_HSV2BGR)

    # Apply a thermal color map
    thermal_effect = cv2.applyColorMap(saturated_frame, cv2.COLORMAP_INFERNO)

    return thermal_effect


def simulate_infrared_vision(frame: np.ndarray) -> np.ndarray:
    """
    Simulate Infrared vision by highlighting warmer areas.

    Parameters:
        frame (np.ndarray): The input frame to simulate Infrared vision.

    Returns:
        np.ndarray: The frame with Infrared vision effects.
    """
    # Convert to grayscale to get intensity values
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    normalized_gray = np.empty_like(gray_frame)

    # Normalize the grayscale image to enhance contrast
    cv2.normalize(
        src=gray_frame,
        dst=normalized_gray,
        alpha=0,
        beta=255,
        norm_type=cv2.NORM_MINMAX,
        dtype=cv2.CV_8U,
    )

    # Apply a heat colormap to represent infrared
    infrared_effect = cv2.applyColorMap(normalized_gray, cv2.COLORMAP_JET)

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

    # Enhance edges using adaptive thresholding
    edges = cv2.adaptiveThreshold(
        gray_frame, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    # Create a blank image for the sonar effect
    sonar_effect = np.zeros_like(frame)

    # Draw concentric circles to simulate sonar waves
    center_x, center_y = frame.shape[1] // 2, frame.shape[0] // 2
    max_radius = int(np.hypot(center_x, center_y))
    for radius in range(0, max_radius, 20):
        cv2.circle(sonar_effect, (center_x, center_y), radius, (255, 255, 255), 1)

    # Combine edges with the sonar effect
    edges_colored = cv2.merge([edges, edges, edges])
    combined = cv2.bitwise_or(sonar_effect, edges_colored)

    # Apply a monochromatic colormap
    ultrasonic_effect = cv2.applyColorMap(combined, cv2.COLORMAP_OCEAN)

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


def preprocess_frame_soft_colors(frame: np.ndarray) -> np.ndarray:
    """
    Adjust colors to resemble the softer, natural tones.

    Args:
        frame (np.ndarray): The input frame.

    Returns:
        np.ndarray: The preprocessed frame with softer colors.
    """

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    mono_frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    alpha = 0.5
    beta = 0.5
    frame = cv2.addWeighted(frame, alpha, mono_frame, beta, 0)

    frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=10)

    return frame


def preprocess_frame_fisheye(frame: np.ndarray) -> np.ndarray:
    """
    Apply a fisheye-like distortion effect.

    Args:
        frame (np.ndarray): The input frame.

    Returns:
        np.ndarray: The processed frame.
    """

    height, width = frame.shape[:2]

    camera_matrix = np.array(
        [[width, 0, width / 2], [0, height, height / 2], [0, 0, 1]]
    )
    distortion_coefficients = np.array([-0.4, 0.2, 0, 0])

    map1, map2 = cv2.fisheye.initUndistortRectifyMap(
        camera_matrix,
        distortion_coefficients,
        np.eye(3),
        camera_matrix,
        (width, height),
        cv2.CV_16SC2,
    )
    distorted_frame = cv2.remap(
        frame,
        map1,
        map2,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )

    return distorted_frame


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
