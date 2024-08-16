class Picarx:
    def set_dir_servo_angle(self, angle: int):
        print(f"Setting servo angle to {angle} degrees")

    def forward(self, speed: int):
        print(f"Moving forward with speed {speed}")

    def backward(self, speed: int):
        print(f"Moving backward with speed {speed}")

    def stop(self):
        print("Stopping")

    def set_cam_tilt_angle(self, angle: int):
        print(f"Setting camera tilt angle to {angle} degrees")

    def set_cam_pan_angle(self, angle: int):
        print(f"Setting camera pan angle to {angle} degrees")
