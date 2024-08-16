from multiprocessing import Manager
import time
import threading
import numpy as np
import cv2


class Vilib(object):
    camera_vflip = False
    camera_hflip = False
    camera_run = False

    flask_thread = None
    camera_thread = None
    flask_start = False

    qrcode_display_thread = None
    qrcode_making_completed = False
    qrcode_img = Manager().list(range(1))
    qrcode_img_encode = None
    qrcode_win_name = "qrcode"

    img = Manager().list(range(1))
    flask_img = Manager().list(range(1))

    Windows_Name = "picamera"
    imshow_flag = False
    web_display_flag = False
    imshow_qrcode_flag = False
    web_qrcode_flag = False

    draw_fps = False
    fps_origin = (640 - 105, 20)
    fps_size = 0.6
    fps_color = (255, 255, 255)

    detect_obj_parameter = {}
    color_detect_color = None
    face_detect_sw = False
    hands_detect_sw = False
    pose_detect_sw = False
    image_classify_sw = False
    image_classification_model = None
    image_classification_labels = None
    objects_detect_sw = False
    objects_detection_model = None
    objects_detection_labels = None
    qrcode_detect_sw = False
    traffic_detect_sw = False

    @staticmethod
    def mock_camera():
        frame_shape = (480, 640, 3)
        x = 0
        y = 0
        dx = 5
        dy = 5
        while Vilib.camera_run:
            frame = np.zeros(frame_shape, dtype=np.uint8)
            x += dx
            y += dy
            if x <= 0 or x >= 540:
                dx = -dx
            if y <= 0 or y >= 400:
                dy = -dy
            cv2.circle(frame, (x, y), 20, (255, 255, 255), -1)  # Draw a moving circle

            # Mock image data and functionalities
            Vilib.img = frame

            # Copy image data for Flask streaming
            Vilib.flask_img = frame

            # Display on desktop
            if Vilib.imshow_flag:
                cv2.imshow(Vilib.Windows_Name, frame)
                cv2.waitKey(1)

            time.sleep(0.033)  # ~30 FPS

        cv2.destroyAllWindows()

    @staticmethod
    def camera_start(vflip=False, hflip=False):
        print(f"Starting camera with vflip={vflip}, hflip={hflip}")
        Vilib.camera_hflip = hflip
        Vilib.camera_vflip = vflip
        Vilib.camera_run = True
        Vilib.camera_thread = threading.Thread(target=Vilib.mock_camera, name="vilib")
        Vilib.camera_thread.daemon = False
        Vilib.camera_thread.start()

    @staticmethod
    def camera_close():
        print("Closing camera")
        if Vilib.camera_thread is not None:
            Vilib.camera_run = False
            time.sleep(0.1)

    @staticmethod
    def display(local=True, web=True):
        print(f"Displaying camera feed with local={local}, web={web}")

    @staticmethod
    def take_photo(photo_name, path):
        print(f"Taking photo '{photo_name}' at path {path}")

    @staticmethod
    def show_fps(color=None, fps_size=None, fps_origin=None):
        if color is not None:
            Vilib.fps_color = color
        if fps_size is not None:
            Vilib.fps_size = fps_size
        if fps_origin is not None:
            Vilib.fps_origin = fps_origin
        Vilib.draw_fps = True

    @staticmethod
    def hide_fps():
        Vilib.draw_fps = False
