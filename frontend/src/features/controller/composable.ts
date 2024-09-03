import { ref, computed, onMounted, onUnmounted } from "vue";
import { renameKeys } from "rename-obj-map";
import { useControllerStore } from "@/features/controller/store";
import { useSettingsStore } from "@/features/settings/stores";
import type { ControllerActionName } from "@/features/controller/store";
import { formatKeyEventItem, formatKeyboardEvents } from "@/util/keyboard-util";
import { groupKeys } from "@/features/settings/util";
import { usePopupStore } from "@/features/settings/stores";
import { calibrationModeRemap } from "@/features/settings/defaultKeybindings";

export const useCarController = (
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

  const settingsKeybindings = computed(
    () => settingsStore.settings.keybindings,
  );

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

  const handleKeyUp = (event: KeyboardEvent) => {
    const key = formatKeyEventItem(event);
    activeKeys.value.delete(key);
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (popupStore.isOpen) {
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

  const updateCarState = () => {
    const leftKey = findKey(settingsKeybindings.value.left);
    const rightKey = findKey(settingsKeybindings.value?.right);
    const stopKey = findKey(settingsKeybindings.value?.stop);

    if (findKey(settingsKeybindings.value?.accelerate)) {
      controllerStore.accelerate();
    } else if (findKey(settingsKeybindings.value?.decelerate)) {
      controllerStore.decelerate();
    } else if (!controllerStore.avoidObstacles) {
      controllerStore.slowdown();
    }

    if (leftKey) {
      inactiveKeys.value.add(leftKey);
      controllerStore.left();
    } else if (rightKey) {
      inactiveKeys.value.add(rightKey);
      controllerStore.right();
    } else if (inactiveKeys.value.size > 0) {
      inactiveKeys.value.clear();
      controllerStore.resetDirServoAngle();
    }

    if (stopKey) {
      controllerStore.stop();
    }
  };

  onMounted(() => {
    controllerStore.reconnectedEnabled = true;
    if (!controllerStore.connected && !controllerStore.loading) {
      controllerStore.initializeWebSocket(
        "ws://" + window.location.hostname + ":8765",
      );
    }
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    gameLoop();
  });

  onUnmounted(() => {
    if (loopTimer.value) {
      clearTimeout(loopTimer.value);
      loopTimer.value = undefined;
    }
    window.removeEventListener("keydown", handleKeyDown);
    window.removeEventListener("keyup", handleKeyUp);
    controllerStore.cleanup();
  });
};
