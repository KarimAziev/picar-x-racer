import { ref, onMounted, onBeforeUnmount } from "vue";
import nipplejs from "nipplejs";
import type { JoystickManagerOptions } from "nipplejs";
import { useControllerStore } from "@/features/controller/store";

export const useJoystickCameraControl = (
  controllerStore: ReturnType<typeof useControllerStore>,
  options?: JoystickManagerOptions,
) => {
  const joystickZone = ref<HTMLElement | null>(null);
  let joystickManager: nipplejs.JoystickManager;

  const handleJoystickMove = (data: nipplejs.JoystickOutputData) => {
    const { angle, distance } = data;
    const direction = angle.degree;

    if (distance > 10) {
      if (direction > 45 && direction <= 135) {
        controllerStore.increaseCamTilt();
      } else if (direction > 135 && direction <= 225) {
        controllerStore.decreaseCamPan();
      } else if (direction > 225 && direction <= 315) {
        controllerStore.decreaseCamTilt();
      } else {
        controllerStore.increaseCamPan();
      }
    } else {
      controllerStore.resetCameraRotate();
    }
  };

  const handleJoystickEnd = () => {
    controllerStore.stop();
    controllerStore.resetDirServoAngle();
  };

  onMounted(() => {
    if (joystickZone.value) {
      joystickManager = nipplejs.create({
        zone: joystickZone.value!,
        mode: "static",
        position: { right: "20%", top: "50%" },
        color: "red",
        ...options,
      });

      joystickManager.on("move", (_event, data) => {
        handleJoystickMove(data);
      });

      joystickManager.on("end", handleJoystickEnd);
    }
  });

  onBeforeUnmount(() => {
    if (joystickManager) {
      joystickManager.destroy();
    }
  });

  return {
    joystickZone,
  };
};
