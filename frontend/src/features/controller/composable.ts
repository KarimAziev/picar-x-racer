import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { renameKeys } from "rename-obj-map";
import { useControllerStore } from "@/features/controller/store";
import { useSettingsStore } from "@/features/settings/stores";
import type { ControllerActionName } from "@/features/controller/store";
import { formatKeyEventItem, formatKeyboardEvents } from "@/util/keyboard-util";
import { groupKeys } from "@/features/settings/util";
import { usePopupStore } from "@/features/settings/stores";
import { calibrationModeRemap } from "@/features/settings/defaultKeybindings";
import { isMobileDevice } from "@/util/device";

export const useController = (
  controllerStore: ReturnType<typeof useControllerStore>,
  settingsStore: ReturnType<typeof useSettingsStore>,
  popupStore: ReturnType<typeof usePopupStore>,
) => {
  const ignored: ControllerActionName[] = [
    "left",
    "right",
    "accelerate",
    "decelerate",
    "slowdown",
    "stop",
  ];

  const settingsKeybindings = computed(() => settingsStore.data.keybindings);

  const keybindings = computed(() => {
    const data = controllerStore.calibrationMode
      ? groupKeys(
          renameKeys(calibrationModeRemap, { ...settingsKeybindings.value }),
        )
      : groupKeys({ ...settingsKeybindings.value });
    return data;
  });

  const loopTimer = ref();
  const activeKeys = ref(new Set<string>());
  const inactiveKeys = ref(new Set<string>());

  const findKey = (keys?: string[]) =>
    keys && keys.find((k) => activeKeys.value.has(k));

  const findInactiveKey = (keys?: string[]) =>
    keys && keys.find((k) => inactiveKeys.value.has(k));

  const handleKeyUp = (event: KeyboardEvent) => {
    const key = formatKeyEventItem(event);
    activeKeys.value.delete(key);
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (popupStore.isOpen || settingsStore.inhibitKeyHandling) {
      return;
    }

    const key = formatKeyboardEvents([event]);
    const commandName = keybindings.value[key];

    if (commandName) {
      event.preventDefault();

      if (!ignored.includes(commandName) && controllerStore[commandName]) {
        controllerStore[commandName]();
      } else if (!event.repeat) {
        activeKeys.value.add(key);
      }
    }
  };

  const gameLoop = () => {
    updateCarState();
    loopTimer.value = setTimeout(() => gameLoop(), 50);
  };

  const cleanupGameLoop = () => {
    if (loopTimer.value) {
      clearTimeout(loopTimer.value);
      loopTimer.value = undefined;
    }
  };

  const updateCarState = () => {
    const leftKey = findKey(settingsKeybindings.value.left);
    const rightKey = findKey(settingsKeybindings.value?.right);
    const stopKey = findKey(settingsKeybindings.value?.stop);
    const accelerateKey = findKey(settingsKeybindings.value?.accelerate);
    const decelerateKey = findKey(settingsKeybindings.value?.decelerate);

    if (accelerateKey) {
      controllerStore.accelerate();
      inactiveKeys.value.add(accelerateKey);
    } else if (decelerateKey) {
      controllerStore.decelerate();
      inactiveKeys.value.add(decelerateKey);
    } else if (
      stopKey ||
      findInactiveKey(settingsKeybindings.value?.accelerate) ||
      findInactiveKey(settingsKeybindings.value?.decelerate)
    ) {
      if (!controllerStore.avoidObstacles) {
        controllerStore.stop();
      }
      const keys = [
        ...(settingsKeybindings.value?.decelerate || []),
        ...(settingsKeybindings.value?.accelerate || []),
      ];
      keys.forEach((key) => {
        inactiveKeys.value.delete(key);
      });
    }

    if (leftKey) {
      inactiveKeys.value.add(leftKey);
      controllerStore.left();
    } else if (rightKey) {
      inactiveKeys.value.add(rightKey);
      controllerStore.right();
    } else if (
      findInactiveKey(settingsKeybindings.value?.left) ||
      findInactiveKey(settingsKeybindings.value?.right)
    ) {
      controllerStore.resetDirServoAngle();
      const keys = [
        ...(settingsKeybindings.value?.left || []),
        ...(settingsKeybindings.value?.right || []),
      ];
      keys.forEach((key) => {
        inactiveKeys.value.delete(key);
      });
    }
  };
  const cleanup = () => {
    window.removeEventListener("beforeunload", cleanup);
    controllerStore.cleanup();
  };
  const addKeyEventListeners = () => {
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("beforeunload", cleanup);
  };

  const removeKeyEventListeners = () => {
    window.removeEventListener("keydown", handleKeyDown);
    window.removeEventListener("keyup", handleKeyUp);
    window.removeEventListener("cleanup", cleanup);
  };

  const connectWS = () => {
    controllerStore.initializeWebSocket();
  };

  return {
    cleanupGameLoop,
    loopTimer,
    updateCarState,
    gameLoop,
    handleKeyDown,
    handleKeyUp,
    addKeyEventListeners,
    removeKeyEventListeners,
    connectWS,
    cleanup,
  };
};

export const useCarController = (
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
  } = useController(controllerStore, settingsStore, popupStore);

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
