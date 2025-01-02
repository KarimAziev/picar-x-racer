import { ref, onMounted, onBeforeUnmount } from "vue";
import nipplejs from "nipplejs";
import type { JoystickManagerOptions } from "nipplejs";
import {
  useControllerStore,
  SERVO_DIR_ANGLE_MIN,
  SERVO_DIR_ANGLE_MAX,
} from "@/features/controller/store";
import { roundToNearestTen } from "@/util/number";
import { constrain } from "@/util/constrain";

export interface Callbacks {
  onStart?: (outputData: nipplejs.JoystickOutputData) => void;
  onEnd?: (outputData: nipplejs.JoystickOutputData) => void;
}

export const useJoystickControl = (
  controllerStore: ReturnType<typeof useControllerStore>,
  options?: JoystickManagerOptions,
  handlers?: Callbacks,
) => {
  const joystickZone = ref<HTMLElement | null>(null);
  const joystickManager = ref<nipplejs.JoystickManager | null>(null);
  const optionsParams = ref<JoystickManagerOptions | undefined>(options);

  const handleJoystickMove = (data: nipplejs.JoystickOutputData) => {
    const { angle, distance } = data;
    const direction = angle.degree;

    const speed = Math.round(Math.round(distance * 2) / 10) * 10;
    const minJoystickAngle = 0;
    const maxJoystickAngle = 180;

    const minServoAngle = 30;
    const maxServoAngle = -30;
    const isForward = direction <= 180;

    const servoDir = roundToNearestTen(
      constrain(
        SERVO_DIR_ANGLE_MIN,
        SERVO_DIR_ANGLE_MAX,
        (((isForward ? direction : direction - 180) - minJoystickAngle) *
          (maxServoAngle - minServoAngle)) /
          (maxJoystickAngle - minJoystickAngle) +
          minServoAngle,
      ),
    );

    const servoDirNotLocked = !optionsParams.value?.lockY;

    if (isForward) {
      if (servoDirNotLocked) {
        controllerStore.setDirServoAngle(servoDir);
      }

      if (!optionsParams.value?.lockX) {
        controllerStore.forward(speed);
      }
    } else {
      if (servoDirNotLocked) {
        controllerStore.setDirServoAngle(-servoDir);
      }

      if (!optionsParams.value?.lockX) {
        controllerStore.backward(speed);
      }
    }
  };

  const handleJoystickEnd = (
    _evt: nipplejs.EventData,
    data: nipplejs.JoystickOutputData,
  ) => {
    if (handlers?.onEnd) {
      handlers?.onEnd(data);
    }
  };

  const handleDestroyJoysticManager = () => {
    if (joystickManager.value) {
      joystickManager.value.destroy();
    }
  };

  const handleCreateJoysticManager = (params?: JoystickManagerOptions) => {
    if (joystickZone.value) {
      const styles = getComputedStyle(document.documentElement);
      const color = styles.getPropertyValue("--color-text").trim();
      joystickManager.value = nipplejs.create({
        zone: joystickZone.value!,
        dynamicPage: true,
        mode: "static",
        position: { left: "20%", bottom: "50%" },
        color: color,
        ...params,
      });

      joystickManager.value.on("start", (_event, data) => {
        if (handlers?.onStart) {
          handlers?.onStart(data);
        }
      });

      joystickManager.value.on("move", (_event, data) => {
        handleJoystickMove(data);
      });

      joystickManager.value.on("end", handleJoystickEnd);
    }
  };

  const restartJoysticManager = () => {
    handleDestroyJoysticManager();
    handleCreateJoysticManager({ ...optionsParams.value });
  };

  const recreateJoysticManager = (params?: JoystickManagerOptions) => {
    optionsParams.value = { ...optionsParams.value, ...params };
    handleDestroyJoysticManager();
    handleCreateJoysticManager(params);
  };

  onMounted(() => {
    controllerStore.initializeWebSocket();
    window.addEventListener("resize", restartJoysticManager);
    window.addEventListener("orientationchange", restartJoysticManager);
    handleCreateJoysticManager(optionsParams.value);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", restartJoysticManager);
    window.removeEventListener("orientationchange", restartJoysticManager);
    handleDestroyJoysticManager();
    controllerStore.cleanup();
  });

  return {
    params: optionsParams,
    joystickZone,
    joystickManager,
    restartJoysticManager,
    handleDestroyJoysticManager,
    handleCreateJoysticManager,
    recreateJoysticManager,
  };
};
