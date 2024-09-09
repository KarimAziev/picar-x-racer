import cv2
import numpy as np

highlight_color = (191, 255, 0)

def highlight_black_areas(frame: np.ndarray) -> np.ndarray:
    """
    Detect black colors in an image and highlight them by drawing
    a border with the color (191, 255, 0).

    Parameters:
        frame (np.ndarray): The input image in which to detect black areas.

    Returns:
        np.ndarray: The image with highlighted black areas.
    """

    threshold = 10  # Threshold to consider a pixel as black

    # Define lower and upper bounds for black color as numpy arrays
    lower_bound = np.array([0, 0, 0])
    upper_bound = np.array([threshold, threshold, threshold])

    # Create a mask for black colors
    black_mask = cv2.inRange(frame, lower_bound, upper_bound)

    # Find contours in the mask
    contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Draw contours on the original image
    frame_with_highlight = frame.copy()
    cv2.drawContours(frame_with_highlight, contours, -1, highlight_color, 2)

    return frame_with_highlight

def highlight_red_areas(frame: np.ndarray) -> np.ndarray:
    """
    Detect red colors in an image and highlight them by drawing
    a border with the color (191, 255, 0).

    Parameters:
        frame (np.ndarray): The input image in which to detect red areas.

    Returns:
        np.ndarray: The image with highlighted red areas.
    """

    # Define lower and upper bounds for red color in HSV color space
    lower_bound1 = np.array([0, 100, 100])
    upper_bound1 = np.array([10, 255, 255])
    lower_bound2 = np.array([160, 100, 100])
    upper_bound2 = np.array([180, 255, 255])

    # Convert the frame to HSV color space
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Create masks for red color
    red_mask1 = cv2.inRange(hsv_frame, lower_bound1, upper_bound1)
    red_mask2 = cv2.inRange(hsv_frame, lower_bound2, upper_bound2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)

    # Find contours in the mask
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Draw contours on the original image
    frame_with_highlight = frame.copy()
    cv2.drawContours(frame_with_highlight, contours, -1, highlight_color, 2)

    return frame_with_highlight

def highlight_blue_areas(frame: np.ndarray) -> np.ndarray:
    """
    Detect blue colors in an image and highlight them by drawing
    a border with the color (191, 255, 0).

    Parameters:
        frame (np.ndarray): The input image in which to detect blue areas.

    Returns:
        np.ndarray: The image with highlighted blue areas.
    """

    # Define lower and upper bounds for blue color in HSV color space
    lower_bound = np.array([100, 150, 0])
    upper_bound = np.array([140, 255, 255])

    # Convert the frame to HSV color space
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Create a mask for blue color
    blue_mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)

    # Find contours in the mask
    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Draw contours on the original image
    frame_with_highlight = frame.copy()
    cv2.drawContours(frame_with_highlight, contours, -1, highlight_color, 2)

    return frame_with_highlight

def highlight_white_areas(frame: np.ndarray) -> np.ndarray:
    """
    Detect white colors in an image and highlight them by drawing
    a border with the color (191, 255, 0).

    Parameters:
        frame (np.ndarray): The input image in which to detect white areas.

    Returns:
        np.ndarray: The image with highlighted white areas.
    """

    # Define lower and upper bounds for white color
    lower_bound = np.array([200, 200, 200])
    upper_bound = np.array([255, 255, 255])

    # Create a mask for white colors
    white_mask = cv2.inRange(frame, lower_bound, upper_bound)

    # Find contours in the mask
    contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Draw contours on the original image
    frame_with_highlight = frame.copy()
    cv2.drawContours(frame_with_highlight, contours, -1, highlight_color, 2)

    return frame_with_highlight