import { ref, onMounted, onBeforeUnmount } from "vue";
import nipplejs from "nipplejs";
import type { JoystickManagerOptions } from "nipplejs";
import { useControllerStore } from "@/features/controller/store";

export const useJoystickControl = (
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
        controllerStore.accelerate();
      } else if (direction > 135 && direction <= 225) {
        controllerStore.left();
      } else if (direction > 225 && direction <= 315) {
        controllerStore.decelerate();
      } else {
        controllerStore.right();
      }
    } else {
      controllerStore.slowdown();
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
        dynamicPage: true,
        mode: "static",
        position: { left: "20%", bottom: "50%" },
        color: "#00ffbf",
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
