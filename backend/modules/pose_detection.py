#!/usr/bin/env python3
import cv2

from ast import literal_eval
import mediapipe.python.solutions.drawing_utils as mp_drawing
import mediapipe.python.solutions.pose as mp_pose

mp_drawing = drawing_utils  # type: ignore
mp_pose = pose  # type: ignore


class DetectPose:
    def __init__(self):
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )

    def work(self, image):
        joints = []
        if len(image) != 0:
            # To improve performance, optionally mark the image as not writeable to
            # pass by reference.
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.pose.process(image)

            # Draw the pose annotation on the image.
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.pose_landmarks:  # Check if landmarks are detected
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,  # Correct attribute access
                    mp_pose.POSE_CONNECTIONS,  # This should be the correct type
                )

                joints = (
                    str(results.pose_landmarks)  # Correct attribute access
                    .replace("\n", "")
                    .replace(" ", "")
                    .replace("landmark", ",")
                    .replace(",", "", 1)
                )
                joints = (
                    "["
                    + joints.replace("{x:", "[")
                    .replace("y:", ",")
                    .replace("z:", ",")
                    .replace("visibilit", "")
                    .replace("}", "]")
                    + "]"
                )
                try:
                    joints = literal_eval(joints)
                except Exception as e:
                    raise (e)
            return image, joints
