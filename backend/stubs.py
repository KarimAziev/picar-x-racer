from multiprocessing import Manager


class FakePicarx:
    def set_dir_servo_angle(self, angle):
        print(f"Setting servo angle to {angle} degrees")

    def forward(self, speed):
        print(f"Moving forward with speed {speed}")

    def backward(self, speed):
        print(f"Moving backward with speed {speed}")

    def stop(self):
        print("Stopping")

    def set_cam_tilt_angle(self, angle):
        print(f"Setting camera tilt angle to {angle} degrees")

    def set_cam_pan_angle(self, angle):
        print(f"Setting camera pan angle to {angle} degrees")


class FakeVilib(object):
    flask_img = Manager().list(range(1))

    @staticmethod
    def take_photo(name, path):
        print(f"Taking photo '{name}' at path {path}")

    @staticmethod
    def camera_start(vflip=False, hflip=False):
        print(f"Starting camera with vflip={vflip}, hflip={hflip}")

    @staticmethod
    def display(local=True, web=True):
        print(f"Displaying camera feed with local={local}, web={web}")

    @staticmethod
    def camera_close():
        print("Closing camera")


class FakeMusic:
    @staticmethod
    def music_play(track_path):
        print(f"Playing music from {track_path}")

    @staticmethod
    def music_stop():
        print("Stopping music")

    @staticmethod
    def sound_play(sound_path):
        print(f"Playing sound from {sound_path}")

    @staticmethod
    def music_set_volume(volume):
        print(f"Setting music volume to {volume}")


def fake_reset_mcu():
    print("Resetting MCU")
