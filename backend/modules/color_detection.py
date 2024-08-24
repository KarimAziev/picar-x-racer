import cv2
from typing import List, Tuple, Union, cast
import numpy as np


def find_contours(
    image: np.ndarray,
) -> Tuple[List[np.ndarray], Union[np.ndarray, None]]:
    """Wrapper around cv2.findContours to handle different OpenCV versions."""
    _tuple = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(_tuple) == 3:
        contours = cast(List[np.ndarray], _tuple[1])
        hierarchy = cast(Union[np.ndarray, None], _tuple[2])
    elif len(_tuple) == 2:
        contours = cast(List[np.ndarray], _tuple[0])
        hierarchy = cast(Union[np.ndarray, None], _tuple[1])
    else:
        raise ValueError("Unexpected number of return values from cv2.findContours")

    return contours, hierarchy


"""The range of H, S, V in HSV space for colors"""
# You can run ../examples/hsv_threshold_analyzer.py to analyze and adjust these values
color_dict = {
    "red": [[0, 8], [80, 255], [0, 255]],
    "orange": [[12, 18], [80, 255], [80, 255]],
    "yellow": [[20, 60], [60, 255], [120, 255]],
    "green": [[45, 85], [120, 255], [80, 255]],
    "blue": [[92, 120], [120, 255], [80, 255]],
    "purple": [[115, 155], [30, 255], [60, 255]],
    "magenta": [[160, 180], [30, 255], [60, 255]],
}


"""Define parameters for color detection object"""
color_obj_parameter = {}

color_obj_parameter["color"] = "red"  # color to be detected

color_obj_parameter["x"] = 320  # the largest color block center x-axis coordinate
color_obj_parameter["y"] = 240  # the largest color block center y-axis coordinate
color_obj_parameter["w"] = 0  # the largest color block pixel width
color_obj_parameter["h"] = 0  # the largest color block pixel height
color_obj_parameter["n"] = 0  # Number of color blocks detected


color_obj_parameter = {}


def color_detect_work(img, width, height, color_name, rectangle_color=(0, 0, 255)):
    """
    Color detection with opencv

    :param img: The detected image data
    :type img: list
    :param width: The width of the image data
    :type width: int
    :param height: The height of the image data
    :type height: int
    :param color_name: The name of the color to be detected. Eg: "red". For supported colors, please see [color_dict].
    :type color_name: str
    :param rectangle_color: The color (BGR, tuple) of rectangle. Eg: (0, 0, 255).
    :type rectangle_color: tuple
    :returns: The image returned after detection.
    :rtype: Binary list
    """
    color_obj_parameter["color"] = color_name

    # Reduce image for faster recognition
    zoom = 4  # reduction ratio
    width_zoom = int(width / zoom)
    height_zoom = int(height / zoom)
    resize_img = cv2.resize(
        img, (width_zoom, height_zoom), interpolation=cv2.INTER_LINEAR
    )

    # Convert the image from BGR to HSV
    hsv = cv2.cvtColor(resize_img, cv2.COLOR_BGR2HSV)

    # Set range for the color and define mask
    color_lower = np.array(
        [
            min(color_dict[color_name][0]),
            min(color_dict[color_name][1]),
            min(color_dict[color_name][2]),
        ]
    )
    color_upper = np.array(
        [
            max(color_dict[color_name][0]),
            max(color_dict[color_name][1]),
            max(color_dict[color_name][2]),
        ]
    )

    mask = cv2.inRange(hsv, color_lower, color_upper)

    if color_name == "red":
        mask_2 = cv2.inRange(hsv, np.array([167, 0, 0]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask, mask_2)

    # Define a 5×5 kernel
    kernel_5 = np.ones((5, 5), np.uint8)

    # Opening the image (erosion followed by dilation), to remove the image noise
    open_img = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_5, iterations=1)

    # Find contours in binary image
    contours, _ = find_contours(open_img)

    color_obj_parameter["n"] = len(contours)

    if color_obj_parameter["n"] < 1:
        color_obj_parameter["x"] = width / 2
        color_obj_parameter["y"] = height / 2
        color_obj_parameter["w"] = 0
        color_obj_parameter["h"] = 0
        color_obj_parameter["n"] = 0
    else:
        # Iterate over all contours
        max_area = 0
        for contour in contours:
            # Return the coordinate(top left), width, and height of contour
            x, y, w, h = cv2.boundingRect(contour)
            if w >= 8 and h >= 8:
                x = x * zoom
                y = y * zoom
                w = w * zoom
                h = h * zoom
                # Draw rectangle around the color block
                cv2.rectangle(
                    img,  # image
                    (x, y),  # start position
                    (x + w, y + h),  # end position
                    rectangle_color,  # color
                    2,  # thickness
                )
                # Draw color name
                cv2.putText(
                    img,  # image
                    color_name,  # text
                    (x, y - 5),  # start position
                    cv2.FONT_HERSHEY_SIMPLEX,  # font
                    0.72,  # font size
                    rectangle_color,  # color
                    1,  # thickness
                    cv2.LINE_AA,  # line_type: LINE_8 (default), LINE_4, LINE_AA
                )
            else:
                continue

            # Save the attribute of the largest color block
            object_area = w * h
            if object_area > max_area:
                max_area = object_area
                color_obj_parameter["x"] = int(x + w / 2)
                color_obj_parameter["y"] = int(y + h / 2)
                color_obj_parameter["w"] = w
                color_obj_parameter["h"] = h

    return img


# Test
def test(color):
    print("color detection: %s" % color)

    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            # If loading a video, use 'break' instead of 'continue'.
            continue

        # frame = cv2.flip(frame, -1) # Flip camera vertically

        out_img = color_detect_work(frame, 640, 480, color)

        cv2.imshow("Color detecting ...", out_img)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        if cv2.waitKey(1) & 0xFF == 27:  # press 'ESC' to quit
            break
        if cv2.getWindowProperty("Color detecting ...", 1) < 0:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test("red")
