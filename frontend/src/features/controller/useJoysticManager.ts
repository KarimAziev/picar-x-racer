import { ref, onMounted, onBeforeUnmount } from "vue";
import nipplejs from "nipplejs";
import type { JoystickManagerOptions } from "nipplejs";
import {
  useControllerStore,
  SERVO_DIR_ANGLE_MIN,
  SERVO_DIR_ANGLE_MAX,
} from "@/features/controller/store";

import { constrain } from "@/util/constrain";

export const useJoystickControl = (
  controllerStore: ReturnType<typeof useControllerStore>,
  options?: JoystickManagerOptions,
) => {
  const joystickZone = ref<HTMLElement | null>(null);
  const joystickManager = ref<nipplejs.JoystickManager | null>(null);

  const handleJoystickMove = (data: nipplejs.JoystickOutputData) => {
    const { angle, distance } = data;
    const direction = angle.degree;
    const speed = Math.round(Math.round(distance * 2) / 10) * 10;
    const minJoystickAngle = 0;
    const maxJoystickAngle = 180;

    const minServoAngle = 30;
    const maxServoAngle = -30;
    const isForward = direction <= 180;

    const servoDir = Math.round(
      constrain(
        SERVO_DIR_ANGLE_MIN,
        SERVO_DIR_ANGLE_MAX,
        (((isForward ? direction : direction - 180) - minJoystickAngle) *
          (maxServoAngle - minServoAngle)) /
          (maxJoystickAngle - minJoystickAngle) +
          minServoAngle,
      ),
    );

    if (isForward) {
      controllerStore.setDirServoAngle(servoDir);
      if (!options?.lockX) {
        controllerStore.forward(speed);
      }
    } else {
      controllerStore.setDirServoAngle(-servoDir);

      if (!options?.lockX) {
        controllerStore.backward(speed);
      }
    }
  };

  const handleJoystickEnd = () => {
    controllerStore.stop();
    controllerStore.resetDirServoAngle();
  };

  const handleDestroyJoysticManager = () => {
    if (joystickManager.value) {
      joystickManager.value.destroy();
    }
  };

  const handleCreateJoysticManager = () => {
    if (joystickZone.value) {
      joystickManager.value = nipplejs.create({
        zone: joystickZone.value!,
        dynamicPage: true,
        mode: "static",
        position: { left: "20%", bottom: "50%" },
        color: "#00ffbf",
        ...options,
      });

      joystickManager.value.on("move", (_event, data) => {
        handleJoystickMove(data);
      });

      joystickManager.value.on("end", handleJoystickEnd);
    }
  };

  const recreateJoysticManager = () => {
    handleDestroyJoysticManager();
    handleCreateJoysticManager();
  };

  onMounted(() => {
    window.addEventListener("resize", recreateJoysticManager);
    window.addEventListener("orientationchange", recreateJoysticManager);
    handleCreateJoysticManager();
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", recreateJoysticManager);
    window.removeEventListener("orientationchange", recreateJoysticManager);
    handleDestroyJoysticManager();
  });

  return {
    joystickZone,
  };
};
