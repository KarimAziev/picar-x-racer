<template>
  <div class="fullscreen-switch">
    <ToggleSwitch
      inputId="fullscreen-toggle"
      v-tooltip="'Toggle Fullscreen'"
      v-model="settingsStore.settings.fullscreen"
    />
  </div>
</template>

<script setup lang="ts">
import ToggleSwitch from "primevue/toggleswitch";
import { watch, onMounted, onBeforeUnmount } from "vue";
import { useSettingsStore } from "@/features/settings/stores";
import { useScrollLock } from "@/composables/useScrollLock";

const settingsStore = useSettingsStore();
const {
  updateAppHeight,
  unlockScroll,
  addResizeListeners,
  removeResizeListeners,
  isLocked,
} = useScrollLock();

watch(
  () => settingsStore.settings.fullscreen,
  (newVal) => {
    try {
      if (!newVal) {
        console.log("unlocking scroll on value change");
        unlockScroll();
      } else {
        console.log("locking scroll on value change");
        isLocked.value = true;
      }
    } catch (error) {}
  },
);

onMounted(() => {
  addResizeListeners();
  updateAppHeight();
  if (settingsStore.settings.fullscreen) {
    isLocked.value = true;
  }
});

onBeforeUnmount(() => {
  removeResizeListeners();
  unlockScroll();
});
</script>

<style scoped lang="scss">
.fullscreen-switch {
  position: absolute;
  right: 10px;
  top: 10px;
  z-index: 12;
}
</style>
