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
import { watch } from "vue";
import { useSettingsStore } from "@/features/settings/stores";

const settingsStore = useSettingsStore();

watch(
  () => settingsStore.settings.fullscreen,
  (newVal) => {
    try {
      if (!newVal) {
        document.exitFullscreen();
      } else {
        document.documentElement.requestFullscreen({ navigationUI: "hide" });
      }
    } catch (error) {}
  },
);
</script>

<style scoped lang="scss">
.fullscreen-switch {
  position: absolute;
  right: 10px;
  top: 10px;
  z-index: 12;
}
</style>
