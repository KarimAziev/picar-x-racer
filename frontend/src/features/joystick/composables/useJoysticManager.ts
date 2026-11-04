import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import nipplejs from "nipplejs";
import type { JoystickManagerOptions } from "nipplejs";
import { useControllerStore } from "@/features/controller/store";
import { inRange } from "@/util/number";
import { constrain } from "@/util/constrain";
import { useRobotStore } from "@/features/settings/stores";

export interface Callbacks {
  onStart?: (outputData: nipplejs.JoystickOutputData) => void;
  onEnd?: (outputData: nipplejs.JoystickOutputData) => void;
}

export const BACKWARD_MIN = 210;
export const BACKWARD_MAX = 330;

export const MIN_JOYSTICK_ANGLE = 0;
export const HALF_CIRCLE_MAX = 180;

export const useJoystickControl = (
  controllerStore: ReturnType<typeof useControllerStore>,
  robotStore: ReturnType<typeof useRobotStore>,
  options?: JoystickManagerOptions,
  handlers?: Callbacks,
) => {
  const joystickZone = ref<HTMLElement | null>(null);
  const joystickManager = ref<nipplejs.JoystickManager | null>(null);
  const optionsParams = ref<JoystickManagerOptions | undefined>(options);

  let active = false;
  let lastData: nipplejs.JoystickOutputData | undefined;
  let restartTimer: ReturnType<typeof setTimeout> | undefined;

  const finishGesture = () => {
    if (!active) return;
    active = false;
    // Stop also cancels the repeating motion command, even before telemetry arrives.
    if (!optionsParams.value?.lockX) controllerStore.stop();
    if (lastData) handlers?.onEnd?.(lastData);
    lastData = undefined;
  };

  const handleJoystickMove = (data: nipplejs.JoystickOutputData) => {
    if (!active) return;
    lastData = data;
    const { angle, distance } = data;
    const direction = angle.degree;

    const isPlainForward = inRange(
      direction,
      MIN_JOYSTICK_ANGLE,
      HALF_CIRCLE_MAX,
    );
    const isExtraForward =
      !isPlainForward && !inRange(direction, BACKWARD_MIN, BACKWARD_MAX);
    const isForward = isPlainForward || isExtraForward;

    const speed = Math.round(Math.round(distance * 2) / 10) * 10;

    const minServoAngle = robotStore.data.steering_servo.min_angle;
    const maxServoAngle = robotStore.data.steering_servo.max_angle;

    const directionWithinRange =
      (isPlainForward ? direction : direction - HALF_CIRCLE_MAX) -
      MIN_JOYSTICK_ANGLE;

    const steeringFraction = constrain(
      -1,
      1,
      (1 - (2 * directionWithinRange) / HALF_CIRCLE_MAX) *
        (isExtraForward ? -1 : 1) *
        (isForward ? 1 : -1),
    );
    const servoDir = Math.round(
      steeringFraction < 0
        ? -steeringFraction * minServoAngle
        : steeringFraction * maxServoAngle,
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
        controllerStore.setDirServoAngle(servoDir);
      }

      if (!optionsParams.value?.lockX) {
        controllerStore.backward(speed);
      }
    }
  };

  const handleDestroyJoysticManager = () => {
    finishGesture();
    joystickManager.value?.destroy();
    joystickManager.value = null;
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
        active = true;
        lastData = data;
        if (handlers?.onStart) {
          handlers?.onStart(data);
        }
      });

      joystickManager.value.on("move", (_event, data) => {
        handleJoystickMove(data);
      });

      joystickManager.value.on("end", finishGesture);
    }
  };

  const restartJoysticManager = () => {
    finishGesture();
    clearTimeout(restartTimer);
    restartTimer = setTimeout(() => {
      handleDestroyJoysticManager();
      handleCreateJoysticManager({ ...optionsParams.value });
    }, 500);
  };

  const recreateJoysticManager = (params?: JoystickManagerOptions) => {
    clearTimeout(restartTimer);
    handleDestroyJoysticManager();
    optionsParams.value = { ...optionsParams.value, ...params };
    handleCreateJoysticManager(optionsParams.value);
  };

  const handleVisibilityChange = () => {
    if (document.hidden) finishGesture();
  };

  watch(
    () => controllerStore.model?.connected,
    (connected) => {
      if (!connected) finishGesture();
    },
    { flush: "sync" },
  );

  onMounted(() => {
    controllerStore.initializeWebSocket();
    window.addEventListener("blur", finishGesture);
    window.addEventListener("pagehide", finishGesture);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("resize", restartJoysticManager);
    window.addEventListener("update-primary-palette", restartJoysticManager);
    window.addEventListener("orientationchange", restartJoysticManager);
    handleCreateJoysticManager(optionsParams.value);
  });

  onBeforeUnmount(() => {
    clearTimeout(restartTimer);
    window.removeEventListener("blur", finishGesture);
    window.removeEventListener("pagehide", finishGesture);
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    window.removeEventListener("resize", restartJoysticManager);
    window.removeEventListener("update-primary-palette", restartJoysticManager);
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
