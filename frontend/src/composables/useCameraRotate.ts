import { ref, Ref } from "vue";
import { useControllerStore } from "@/features/controller/store";

export const useCameraRotate = (imgRef: Ref<HTMLImageElement | undefined>) => {
  const controllerStore = useControllerStore();

  const isDragging = ref(false);
  const lastX = ref(0);
  const lastY = ref(0);

  const startDragging = (e: MouseEvent | TouchEvent) => {
    isDragging.value = true;
    const { clientX, clientY } = "touches" in e ? e.touches[0] : e;
    lastX.value = clientX;
    lastY.value = clientY;
  };

  const stopDragging = () => {
    isDragging.value = false;
  };

  const onDrag = (e: MouseEvent | TouchEvent) => {
    if (!isDragging.value) return;
    const { clientX, clientY } = "touches" in e ? e.touches[0] : e;

    const deltaX = clientX - lastX.value;
    const deltaY = clientY - lastY.value;
    lastX.value = clientX;
    lastY.value = clientY;

    adjustCamera(deltaX, deltaY);
  };

  const adjustCamera = (deltaX: number, deltaY: number) => {
    const newPan = controllerStore.camPan + deltaX * 0.5;
    const newTilt = controllerStore.camTilt - deltaY * 0.5;

    controllerStore.setCamPanAngle(newPan);
    controllerStore.setCamTiltAngle(newTilt);
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

  const resetCameraIfCentered = (e: MouseEvent | Touch) => {
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
  };

  const addListeners = () => {
    const imgElement = imgRef.value;
    if (imgElement) {
      imgElement.addEventListener("mousedown", startDragging);
      imgElement.addEventListener("mousemove", onDrag);
      imgElement.addEventListener("mouseup", onMouseUp);
      imgElement.addEventListener("touchstart", startDragging, {
        passive: true,
      });
      imgElement.addEventListener("touchmove", onDrag, { passive: true });
      imgElement.addEventListener("touchend", onTouchEnd);
    }
  };

  const removeListeners = () => {
    const imgElement = imgRef.value;
    if (imgElement) {
      imgElement.addEventListener("mousedown", startDragging);
      imgElement.addEventListener("mousemove", onDrag);
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
