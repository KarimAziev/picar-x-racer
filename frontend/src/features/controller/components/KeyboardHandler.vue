<template>
  <input
    ref="inputRef"
    @keyup.stop="handleKeyUp"
    @keydown.stop="handleKeyDown"
    :tabindex="0"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useControllerStore } from "@/features/controller/store";
import { usePopupStore, useSettingsStore } from "@/features/settings/stores";
import { isButton, isInput } from "@/util/guards";
import { isMobileDevice } from "@/util/device";
import { inputHistoryDirectionByKey } from "@/composables/useInputHistory";
import {
  useKeyboardControls,
  KeyboardEventPred,
} from "@/features/controller/composables/useKeyboardControls";

const inputRef = ref<HTMLInputElement | null>();
const settingsStore = useSettingsStore();
const controllerStore = useControllerStore();
const popupStore = usePopupStore();

const isEventAllowed: KeyboardEventPred = (event) =>
  event.target === inputRef.value ||
  !(
    (isButton(event.target) || isInput(event.target)) &&
    (event.key.length === 1 ||
      Object.hasOwn(inputHistoryDirectionByKey, event.key))
  );

const {
  gameLoop,
  addKeyEventListeners,
  removeKeyEventListeners,
  cleanupGameLoop,
  connectWS,
  cleanup,
  handleKeyDown,
  handleKeyUp,
} = useKeyboardControls(
  controllerStore,
  settingsStore,
  popupStore,
  isEventAllowed,
);

onMounted(() => {
  connectWS();
  addKeyEventListeners();
  if (!isMobileDevice()) {
    gameLoop();
  }
  if (inputRef.value) {
    inputRef.value.focus();
  }
});

onBeforeUnmount(() => {
  cleanupGameLoop();
  removeKeyEventListeners();
  cleanup();
});
</script>

<style scoped lang="scss">
input {
  position: absolute;
  top: 0;
  left: -100%;
}
</style>
