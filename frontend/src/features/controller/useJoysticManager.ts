import { ref, onMounted, onBeforeUnmount } from "vue";
import nipplejs from "nipplejs";
import type { JoystickManagerOptions } from "nipplejs";
import { useControllerStore } from "@/features/controller/store";

export const useJoystickControl = (
  controllerStore: ReturnType<typeof useControllerStore>,
  options?: JoystickManagerOptions,
) => {
  const joystickZone = ref<HTMLElement | null>(null);
  const joystickManager = ref<nipplejs.JoystickManager | null>(null);

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
