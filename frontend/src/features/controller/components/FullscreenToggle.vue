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

import { useSettingsStore } from "@/features/settings/stores";

const settingsStore = useSettingsStore();
</script>

<style scoped lang="scss">
.fullscreen-switch {
  position: fixed;
  right: 40px;
  top: 10px;
  z-index: 12;
}
</style>
