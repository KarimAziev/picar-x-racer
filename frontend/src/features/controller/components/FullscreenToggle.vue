<template>
  <div class="fullscreen-switch">
    <ToggleSwitch
      v-tooltip="'Toggle Fullscreen'"
      id="fullscreen"
      v-model="settingsStore.settings.fullscreen"
    />
  </div>
</template>

<script setup lang="ts">
import ToggleSwitch from "primevue/toggleswitch";
import { useSettingsStore } from "@/features/settings/stores";

const settingsStore = useSettingsStore();
</script>

<style scoped lang="scss">
.fullscreen-switch {
  position: absolute;
  right: 10px;
  top: 10px;
  z-index: 12;
}
</style>
