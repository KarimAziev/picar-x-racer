import { ref, computed, watch } from "vue";
import type { ControllerActionName } from "@/features/controller/store";
import { useControllerStore } from "@/features/controller/store";
import { useSettingsStore, usePopupStore } from "@/features/settings/stores";
import { formatKeyboardEvents } from "@/util/keyboard-util";
import { calibrationModeRemap } from "@/features/settings/defaultKeybindings";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";
import { keyboardInputID } from "@/features/controller/config";
import { isHTMLElement } from "@/util/guards";
import { groupKeys } from "@/features/settings/util";

export type KeyboardEventPred = (event: KeyboardEvent) => boolean;

export const deferredCommandDict: Partial<{
  [P in ControllerActionName]: boolean;
}> = {
  left: true,
  right: true,
  accelerate: true,
  decelerate: true,
  stop: true,
};

export const useKeyboardControls = (
  controllerStore: ReturnType<typeof useControllerStore>,
  settingsStore: ReturnType<typeof useSettingsStore>,
  popupStore: ReturnType<typeof usePopupStore>,
  keyboardEventPred?: KeyboardEventPred,
) => {
  const settingsKeybindings = computed(
    () => settingsStore.data?.keybindings ?? {},
  );

  const tuning = useServoTuningStore();
  const keybindings = computed(() =>
    groupKeys({ ...settingsKeybindings.value }),
  );
  const pressedKeys = new Map<string, string>();

  const loopTimer = ref<ReturnType<typeof setTimeout>>();
  const activeKeys = ref(new Set<string>());
  const inactiveKeys = ref(new Set<string>());

  const findKey = (keys?: string[] | null) =>
    keys && keys.find((k) => activeKeys.value.has(k));

  const findInactiveKey = (keys?: string[] | null) =>
    keys && keys.find((k) => inactiveKeys.value.has(k));

  const releaseKeys = () => {
    activeKeys.value.clear();
    pressedKeys.clear();
  };
  watch(
    () => controllerStore.calibrationMode,
    () => {
      releaseKeys();
      inactiveKeys.value.clear();
    },
    { flush: "sync" },
  );

  const handleKeyUp = (event: KeyboardEvent) => {
    const identity = event.code || event.key.toLowerCase();
    const key = pressedKeys.get(identity);
    if (key) activeKeys.value.delete(key);
    pressedKeys.delete(identity);
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (popupStore.isOpen || settingsStore.inhibitKeyHandling || tuning.pending)
      return;
    const target = event.target;
    if (
      isHTMLElement(target) &&
      target.id !== keyboardInputID &&
      target.closest("input, textarea, select, [contenteditable='true']")
    )
      return;
    if (keyboardEventPred && !keyboardEventPred(event)) return;

    const key = formatKeyboardEvents([event]);
    const commandName = keybindings.value[key];
    if (controllerStore.calibrationMode && event[tuning.modifier]) {
      const baseEvent = {
        key:
          tuning.modifier === "shiftKey" ? event.key.toLowerCase() : event.key,
        code: event.code,
        shiftKey: event.shiftKey,
        altKey: event.altKey,
        metaKey: event.metaKey,
        ctrlKey: event.ctrlKey,
        [tuning.modifier]: false,
      };
      // Arrow names are case-sensitive; only letter keys change with Shift.
      if (event.key.length > 1) baseEvent.key = event.key;
      const baseCommand = keybindings.value[formatKeyboardEvents([baseEvent])];
      const offsetCommand = baseCommand && calibrationModeRemap[baseCommand];
      if (offsetCommand) {
        event.preventDefault();
        releaseKeys();
        controllerStore[offsetCommand]();
        return;
      }
    }
    if (
      controllerStore.calibrationMode &&
      (commandName === "accelerate" || commandName === "decelerate")
    )
      return;
    if (commandName) {
      event.preventDefault();
      if (!deferredCommandDict[commandName]) {
        controllerStore[commandName]();
      } else if (!event.repeat) {
        activeKeys.value.add(key);
        pressedKeys.set(event.code || event.key.toLowerCase(), key);
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
    if (popupStore.isOpen || settingsStore.inhibitKeyHandling || tuning.pending)
      releaseKeys();
    const leftKey = findKey(settingsKeybindings.value?.left);
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
      if (!controllerStore.calibrationMode)
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
    window.addEventListener("blur", releaseKeys);
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("beforeunload", cleanup);
  };

  const removeKeyEventListeners = () => {
    window.removeEventListener("blur", releaseKeys);
    releaseKeys();
    window.removeEventListener("keydown", handleKeyDown);
    window.removeEventListener("keyup", handleKeyUp);
    window.removeEventListener("beforeunload", cleanup);
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
