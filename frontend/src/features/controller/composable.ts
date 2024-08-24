import { ref, computed, onMounted, onUnmounted } from "vue";
import { useControllerStore } from "@/features/controller/store";
import { useSettingsStore } from "@/features/settings/stores";
import type { ControllerActionName } from "@/features/controller/store";
import { formatKeyEventItem } from "@/util/keyboard-util";
import { groupKeys } from "@/features/settings/util";
import { usePopupStore } from "@/features/settings/stores";

export const useCarController = () => {
  const popupStore = usePopupStore();
  const settings = useSettingsStore();
  const store = useControllerStore();
  const ignored: ControllerActionName[] = [
    "left",
    "right",
    "accelerate",
    "decelerate",
    "slowdown",
    "stop",
  ];

  const keybindings = computed(() => groupKeys(settings.settings.keybindings));

  const loopTimer = ref();
  const activeKeys = ref(new Set<string>());
  const inactiveKeys = ref(new Set<string>());

  const handleKeyUp = (event: KeyboardEvent) => {
    const key = formatKeyEventItem(event);
    activeKeys.value.delete(key);
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (popupStore.isOpen) {
      return;
    }

    const key = formatKeyEventItem(event);

    const commandName = keybindings.value[key];

    if (commandName) {
      event.preventDefault();

      if (!ignored.includes(commandName) && store[commandName]) {
        store[commandName]();
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
    const findKey = (keys?: string[]) =>
      keys && keys.find((k) => activeKeys.value.has(k));
    const leftKey = findKey(settings.settings.keybindings?.left);
    const rightKey = findKey(settings.settings.keybindings?.right);
    const stopKey = findKey(settings.settings.keybindings?.stop);

    if (findKey(settings.settings.keybindings?.accelerate)) {
      store.accelerate();
    } else if (findKey(settings.settings.keybindings?.decelerate)) {
      store.decelerate();
    } else if (!store.avoidObstacles) {
      store.slowdown();
    }

    if (leftKey) {
      inactiveKeys.value.add(leftKey);
      store.left();
    } else if (rightKey) {
      inactiveKeys.value.add(rightKey);
      store.right();
    } else if (inactiveKeys.value.size > 0) {
      inactiveKeys.value.clear();
      store.resetDirServoAngle();
    }

    if (stopKey) {
      store.stop();
    }
  };

  onMounted(() => {
    store.reconnectedEnabled = true;
    store.initializeWebSocket("ws://" + window.location.hostname + ":8765");
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
    store.cleanup();
  });
};
