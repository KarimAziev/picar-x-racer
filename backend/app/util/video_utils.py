import cv2
import numpy as np


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Enhance the input video frame by denoising and applying CLAHE.

    Parameters:
        frame (np.ndarray): The input frame to enhance.

    Returns:
        np.ndarray: The enhanced frame.
    """
    denoised_frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
    lab = cv2.cvtColor(denoised_frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    final_frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return final_frame
