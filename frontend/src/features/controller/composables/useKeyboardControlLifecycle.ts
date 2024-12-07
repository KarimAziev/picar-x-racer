import { onBeforeUnmount, onMounted } from "vue";
import { useKeyboardControls } from "@/features/controller/composables/useKeyboardControls";
import { useControllerStore } from "@/features/controller/store";
import { usePopupStore, useSettingsStore } from "@/features/settings/stores";
import { isMobileDevice } from "@/util/device";

export const useKeyboardControlLifecycle = (
  controllerStore: ReturnType<typeof useControllerStore>,
  settingsStore: ReturnType<typeof useSettingsStore>,
  popupStore: ReturnType<typeof usePopupStore>,
) => {
  const {
    gameLoop,
    addKeyEventListeners,
    removeKeyEventListeners,
    cleanupGameLoop,
    connectWS,
    cleanup,
  } = useKeyboardControls(controllerStore, settingsStore, popupStore);

  onMounted(() => {
    connectWS();
    addKeyEventListeners();
    if (!isMobileDevice()) {
      gameLoop();
    }
  });

  onBeforeUnmount(() => {
    cleanupGameLoop();
    removeKeyEventListeners();
    cleanup();
  });
};
