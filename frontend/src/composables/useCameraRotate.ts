import { ref } from "vue";
import type { Ref } from "vue";
import type { ServoConfig } from "@/features/settings/stores/robot";
import type { UpdateCombinedPayload } from "@/features/controller/store";
import { useControllerStore } from "@/features/controller/store";
import { showDirectionalIndicator } from "@/util/dom";
import { debounce } from "@/util/debounce";
import { constrain } from "@/util/constrain";
import { useRobotStore } from "@/features/settings/stores";

export const useCameraRotate = (imgRef: Ref<HTMLImageElement | undefined>) => {
  const controllerStore = useControllerStore();
  const robotStore = useRobotStore();
  const isDragging = ref(false);
  const lastX = ref(0);
  const lastY = ref(0);
  const panAngle = ref<number | null>(null);
  const tiltAngle = ref<number | null>(null);

  const startDragging = (e: MouseEvent | TouchEvent) => {
    isDragging.value = true;
    const { clientX, clientY } = "touches" in e ? e.touches[0] : e;
    lastX.value = clientX;
    lastY.value = clientY;
  };

  const stopDragging = () => {
    isDragging.value = false;
    panAngle.value = null;
    tiltAngle.value = null;
  };

  const updateDeboucned = debounce((payload: UpdateCombinedPayload) => {
    controllerStore.updateCombined(payload);
  }, 50);

  const onDrag = (e: MouseEvent | TouchEvent) => {
    if (!isDragging.value) return;
    const { clientX, clientY } = "touches" in e ? e.touches[0] : e;

    const deltaX = clientX - lastX.value;
    const deltaY = clientY - lastY.value;
    lastX.value = clientX;
    lastY.value = clientY;
    showDirectionalIndicator(deltaX, deltaY);
    adjustCamera(deltaX, deltaY);
  };

  const snapAngle = (
    rawAngle: number,
    currentAngle: number,
    servo: ServoConfig,
  ) => {
    const { min_angle, max_angle, inc_step, dec_step } = servo;
    const step = rawAngle >= currentAngle ? inc_step : Math.abs(dec_step);
    const numSteps = Math.round((rawAngle - min_angle) / step);
    const snapped = min_angle + numSteps * step;
    return constrain(min_angle, max_angle, snapped);
  };

  const adjustCamera = (deltaX: number, deltaY: number) => {
    if (!robotStore.data.cam_pan_servo && !robotStore.data.cam_tilt_servo) {
      return;
    }

    if (panAngle.value === null) {
      panAngle.value = controllerStore.camPan;
    }
    if (tiltAngle.value === null) {
      tiltAngle.value = controllerStore.camTilt;
    }

    const panServo = robotStore.data.cam_pan_servo;
    const tiltServo = robotStore.data.cam_tilt_servo;

    const rawPan = panServo ? panAngle.value + deltaX * 0.5 : panAngle.value;
    const rawTilt = tiltServo
      ? tiltAngle.value - deltaY * 0.5
      : tiltAngle.value;

    const newPan = panServo
      ? snapAngle(rawPan, panAngle.value, panServo)
      : null;
    const newTilt = tiltServo
      ? snapAngle(rawTilt, tiltAngle.value, tiltServo)
      : null;

    updateDeboucned({ camPan: newPan, camTilt: newTilt });

    panAngle.value = newPan;
    tiltAngle.value = newTilt;
  };

  const onMouseUp = (e: MouseEvent) => {
    stopDragging();
    resetCameraIfCentered(e);
  };

  const onTouchEnd = (e: TouchEvent) => {
    stopDragging();
    if (e.changedTouches.length > 0) {
      resetCameraIfCentered(e.changedTouches[0]);
    }
  };

  const resetCameraIfCentered = debounce((e: MouseEvent | Touch) => {
    const imageFeedElement = imgRef.value;
    if (!imageFeedElement) return;

    const rect = imageFeedElement.getBoundingClientRect();
    const { clientX, clientY } = e;

    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const offsetThresholdX = rect.width * 0.15;
    const offsetThresholdY = rect.height * 0.15;

    const isCenteredX = Math.abs(clientX - centerX) <= offsetThresholdX;
    const isCenteredY = Math.abs(clientY - centerY) <= offsetThresholdY;

    if (isCenteredX && isCenteredY) {
      controllerStore.resetCameraRotate();
    }
  }, 50);

  const handleOrientationChange = () => {
    lastX.value = 0;
    lastY.value = 0;
    controllerStore.resetCameraRotate();
  };

  const removeListeners = () => {
    const imgElement = imgRef.value;
    if (imgElement) {
      imgElement.removeEventListener("mousedown", startDragging);
      imgElement.removeEventListener("mousemove", onDrag);
      imgElement.removeEventListener("mouseup", onMouseUp);
      imgElement.removeEventListener("touchstart", startDragging);
      imgElement.removeEventListener("touchmove", onDrag);
      imgElement.removeEventListener("touchend", onTouchEnd);
      imgElement.removeEventListener(
        "orientationchange",
        handleOrientationChange,
      );
    }
  };

  const addListeners = () => {
    const imgElement = imgRef.value;
    if (imgElement) {
      removeListeners();
      imgElement.addEventListener("mousedown", startDragging);
      imgElement.addEventListener("mousemove", onDrag);
      imgElement.addEventListener("orientationchange", handleOrientationChange);
      imgElement.addEventListener("mouseup", onMouseUp);
      imgElement.addEventListener("touchstart", startDragging, {
        passive: true,
      });
      imgElement.addEventListener("touchmove", onDrag, { passive: true });
      imgElement.addEventListener("touchend", onTouchEnd);
    }
  };

  return {
    startDragging,
    onTouchEnd,
    onMouseUp,
    stopDragging,
    resetCameraIfCentered,
    addListeners,
    removeListeners,
  };
};
